"""Browser E2E test for Gemini Enterprise — full campaign pipeline via the GE console UI.

Connects to Chrome via CDP (port 9222), navigates to the GE console,
sends campaign messages, and captures screenshots of:
1. Thinking indicators
2. Hero images inline
3. 15s commercial video
4. Focus group feedback
5. Final PDF campaign brief

Uses ADC credentials for auth.

Usage:
  source trends_and_insights_agent/.env
  DISPLAY=:20 uv run python tests/test_ge_browser_e2e.py
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv("trends_and_insights_agent/.env")

# --- Configuration ---
_deploy_info = {}
if os.path.exists("deployment_info.json"):
    with open("deployment_info.json") as f:
        _deploy_info = json.load(f)

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", _deploy_info.get("project_id", "wortz-project-352116"))
PROJECT_NUMBER = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", _deploy_info.get("project_number", "679926387543"))
GE_ENGINE = _deploy_info.get("ge_engine", "gemini-enterprise-17634901_1763490144996")
GE_AGENT_ID = _deploy_info.get("ge_agent_id", "3607510876288067860")
AE_ENGINE_ID = _deploy_info.get("engine_id", "8788263399906607104")
AE_LOCATION = "us-central1"
AE_RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{AE_LOCATION}/reasoningEngines/{AE_ENGINE_ID}"

SCREENSHOT_DIR = Path("demo_screenshots/ge_browser_e2e")
CDP_URL = "http://localhost:9222"
MAX_WAVES = 45
WAVE_TIMEOUT_MS = 180_000  # 3 min per wave

# GE Console URL — the chat/assistant interface
GE_CONSOLE_BASE = "https://console.cloud.google.com/gemini-enterprise"
GE_CONSOLE_URL = (
    f"{GE_CONSOLE_BASE}/locations/global/engines/{GE_ENGINE}"
    f"/overview/dashboard?project={PROJECT}"
)

# Campaign setup
CAMPAIGN_MSG = (
    "Create a full marketing campaign for Tide Fabric Softener with Hibiscus Scent "
    "targeting Gen Z eco-conscious consumers. Include market research, hero images, "
    "a 15-second commercial video, and focus group evaluation. Generate a final PDF campaign brief."
)

# Pre-populated AE session state
INITIAL_STATE = {
    "brand": "Tide",
    "target_product": "Tide Fabric Softener with Hibiscus Scent",
    "target_audience": "Gen Z eco-conscious consumers who value sustainable products and fresh scents",
    "key_selling_points": "New Hibiscus Scent. Plant-based formula. 2x cleaning power. Biodegradable packaging. Fresh floral fragrance that lasts.",
    "target_search_trends": {"target_search_trends": [
        {"title": "Sustainable Laundry", "description": "Growing interest in eco-friendly laundry products and sustainable cleaning solutions"}
    ]},
    "target_yt_trends": {"target_yt_trends": [
        {"title": "Eco Cleaning Hacks", "description": "YouTube creators sharing sustainable cleaning routines and eco-friendly product reviews"}
    ]},
    "yt_video_analysis": "YouTube trend analysis: Gen Z audiences are highly engaged with sustainable product content. Key themes: eco-friendly lifestyle, plant-based products, aesthetic packaging.",
    "final_select_ad_copies": {"final_select_ad_copies": []},
    "final_select_vis_concepts": {"final_select_vis_concepts": []},
    "img_artifact_keys": {"img_artifact_keys": []},
    "vid_artifact_keys": {"vid_artifact_keys": []},
    "combined_web_search_insights": "",
    "campaign_web_search_insights": "",
    "gs_web_search_insights": "",
    "yt_web_search_insights": "",
    "combined_final_cited_report": "",
    "sources": {},
    "final_report_with_citations": "",
    "autopilot_mode": True,
    "commercial_duration": 15,
    "commercial_artifact": "",
    "campaign_guide_content": "",
    "gcs_folder": "",
}


def get_access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def get_ae_client():
    import vertexai
    client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
    return client.agent_engines.get(name=AE_RESOURCE_NAME)


def create_ae_session(ae) -> str:
    session = ae.create_session(user_id="ge_browser_e2e", state=INITIAL_STATE)
    return session.get("id") if isinstance(session, dict) else str(session)


def get_pipeline_status(ae, session_id: str) -> dict:
    try:
        session = ae.get_session(user_id="ge_browser_e2e", session_id=session_id)
    except Exception as e:
        print(f"  get_session error: {e}")
        return {"stage": "UNKNOWN", "report_len": 0, "num_images": 0,
                "num_videos": 0, "has_commercial": False, "has_focus_group": False,
                "final_report_len": 0}

    state = session.get("state", {}) if isinstance(session, dict) else {}

    report = state.get("combined_final_cited_report", "")
    imgs = state.get("img_artifact_keys", {})
    vids = state.get("vid_artifact_keys", {})
    final = state.get("final_report_with_citations", "")
    commercial = state.get("commercial_artifact", "")
    focus_group = state.get("focus_group_evaluation", "")

    if isinstance(imgs, dict):
        imgs = imgs.get("img_artifact_keys", [])
    if isinstance(vids, dict):
        vids = vids.get("vid_artifact_keys", [])

    report_len = len(report) if isinstance(report, str) else 0
    final_len = len(final) if isinstance(final, str) else 0
    num_images = len(imgs) if isinstance(imgs, list) else 0
    num_videos = len(vids) if isinstance(vids, list) else 0
    has_commercial = bool(commercial)
    has_focus_group = bool(focus_group)

    if final_len > 0:
        stage = "COMPLETE"
    elif has_focus_group:
        stage = "SAVE_REPORT"
    elif report_len < 500:
        stage = "RESEARCH"
    elif not has_commercial:
        stage = "CREATIVE"
    elif not has_focus_group:
        stage = "FOCUS_GROUP"
    else:
        stage = "SAVE_REPORT"

    return {
        "stage": stage, "report_len": report_len, "num_images": num_images,
        "num_videos": num_videos, "has_commercial": has_commercial,
        "has_focus_group": has_focus_group, "final_report_len": final_len,
        "state": state,
    }


async def run_browser_e2e():
    from playwright.async_api import async_playwright

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    print(f"\n{'#'*60}")
    print(f"GE BROWSER E2E TEST — {timestamp}")
    print(f"{'#'*60}")

    # --- Step 1: Create AE session with pre-populated state ---
    print(f"\n{'='*60}")
    print("STEP 1: Create AE session")
    print(f"{'='*60}")
    ae = get_ae_client()
    ae_session_id = create_ae_session(ae)
    print(f"  AE Session: {ae_session_id}")

    # --- Step 2: Connect to Chrome via CDP ---
    print(f"\n{'='*60}")
    print("STEP 2: Connect to Chrome via CDP")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        print(f"  Connected to Chrome: {browser.browser_type.name}")
        print(f"  Contexts: {len(browser.contexts)}")

        # Use existing context (has GCP auth cookies)
        if browser.contexts:
            context = browser.contexts[0]
            print(f"  Using existing context with {len(context.pages)} pages")
        else:
            context = await browser.new_context()
            print(f"  Created new context")

        # --- Step 3: Navigate to GE console ---
        print(f"\n{'='*60}")
        print("STEP 3: Navigate to GE console")
        print(f"{'='*60}")

        page = await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        print(f"  Navigating to: {GE_CONSOLE_URL}")
        await page.goto(GE_CONSOLE_URL, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(5_000)

        # Take initial screenshot
        ss_path = SCREENSHOT_DIR / f"01_ge_dashboard_{timestamp}.png"
        await page.screenshot(path=str(ss_path), full_page=True)
        print(f"  Screenshot: {ss_path}")

        # Check if we landed on login page
        current_url = page.url
        print(f"  Current URL: {current_url[:120]}")

        if "accounts.google.com" in current_url or "signin" in current_url.lower():
            print("  WARNING: Landed on login page — Chrome may not be authenticated")
            print("  Attempting to check if GCP console is accessible...")

        # --- Step 4: Find and interact with the chat interface ---
        print(f"\n{'='*60}")
        print("STEP 4: Find chat interface")
        print(f"{'='*60}")

        # Look for the GE chat/assistant panel — try multiple selectors
        # The GE console typically has a chat input area
        chat_selectors = [
            'textarea[aria-label*="chat" i]',
            'textarea[aria-label*="message" i]',
            'textarea[placeholder*="message" i]',
            'textarea[placeholder*="Ask" i]',
            'div[contenteditable="true"]',
            'input[aria-label*="chat" i]',
            'mat-form-field textarea',
            '[data-test-id="chat-input"]',
            '.chat-input textarea',
            'cfc-chat-input textarea',
            'textarea',
        ]

        chat_input = None
        for selector in chat_selectors:
            try:
                el = await page.wait_for_selector(selector, timeout=3_000)
                if el:
                    is_visible = await el.is_visible()
                    if is_visible:
                        chat_input = el
                        print(f"  Found chat input: {selector}")
                        break
            except Exception:
                continue

        if not chat_input:
            print("  Chat input not found on dashboard — looking for preview/try-it link...")
            # Try navigating to the preview/try-it page
            preview_urls = [
                f"{GE_CONSOLE_BASE}/locations/global/engines/{GE_ENGINE}/preview?project={PROJECT}",
                f"{GE_CONSOLE_BASE}/locations/global/engines/{GE_ENGINE}/assistants/default_assistant?project={PROJECT}",
            ]
            for preview_url in preview_urls:
                print(f"  Trying: {preview_url[:100]}")
                await page.goto(preview_url, wait_until="domcontentloaded", timeout=20_000)
                await page.wait_for_timeout(5_000)

                ss_path = SCREENSHOT_DIR / f"02_ge_preview_{timestamp}.png"
                await page.screenshot(path=str(ss_path), full_page=True)
                print(f"  Screenshot: {ss_path}")

                for selector in chat_selectors:
                    try:
                        el = await page.wait_for_selector(selector, timeout=3_000)
                        if el and await el.is_visible():
                            chat_input = el
                            print(f"  Found chat input: {selector}")
                            break
                    except Exception:
                        continue
                if chat_input:
                    break

        if not chat_input:
            print("  ERROR: Could not find chat input in GE console")
            print("  Falling back to API-driven test with browser screenshot verification")
            # Fall back: run pipeline via API, then navigate to GE to see results
            await _run_api_pipeline_with_browser_screenshots(page, ae, ae_session_id, timestamp)
            return

        # --- Step 5: Send campaign message and iterate ---
        print(f"\n{'='*60}")
        print("STEP 5: Send campaign message")
        print(f"{'='*60}")

        await chat_input.fill(CAMPAIGN_MSG)
        await page.wait_for_timeout(500)

        # Look for send button
        send_selectors = [
            'button[aria-label*="Send" i]',
            'button[aria-label*="submit" i]',
            'button[type="submit"]',
            'mat-icon-button[aria-label*="Send" i]',
            'button:has(mat-icon:text("send"))',
        ]
        sent = False
        for selector in send_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=2_000)
                if btn and await btn.is_visible():
                    await btn.click()
                    sent = True
                    print(f"  Clicked send: {selector}")
                    break
            except Exception:
                continue

        if not sent:
            # Try pressing Enter
            await chat_input.press("Enter")
            print("  Sent via Enter key")

        # --- Step 6: Wait for and screenshot pipeline stages ---
        await _monitor_ge_pipeline(page, ae, ae_session_id, timestamp)

    elapsed = (time.time() - start_time) / 60
    print(f"\n{'='*60}")
    print(f"BROWSER E2E COMPLETE — {elapsed:.1f} minutes")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    print(f"{'='*60}")


async def _run_api_pipeline_with_browser_screenshots(page, ae, session_id, timestamp):
    """Fallback: run pipeline via AE API, screenshot GE console at each stage."""
    print("\n--- API-driven pipeline with browser screenshots ---")

    # Send initial message via AE API
    all_thoughts = 0
    all_chips = 0

    for wave in range(MAX_WAVES):
        msg = "Run the full campaign pipeline for Tide Fabric Softener with Hibiscus Scent." if wave == 0 else "continue"
        print(f"\n=== Wave {wave + 1}/{MAX_WAVES} ===")
        print(f"  Sending: {msg[:60]}...")

        thought_count = 0
        try:
            for event in ae.stream_query(
                message=msg, user_id="ge_browser_e2e", session_id=session_id,
            ):
                if isinstance(event, dict):
                    parts = event.get("content", {}).get("parts", [])
                    for part in parts:
                        if isinstance(part, dict):
                            if part.get("thought"):
                                thought_count += 1
                            elif part.get("text"):
                                preview = part["text"][:200]
                                author = event.get("author", "?")
                                print(f"  [{author}]: {preview}")
        except Exception as e:
            err = str(e)
            if "FAILED_PRECONDITION" in err or "Service Unavailable" in err:
                print(f"  Transient error, waiting 30s: {err[:100]}")
                await asyncio.sleep(30)
                continue
            print(f"  ERROR: {e}")

        all_thoughts += thought_count
        print(f"  Thoughts in wave: {thought_count}")

        status = get_pipeline_status(ae, session_id)
        stage = status["stage"]
        print(f"  Stage: {stage}")

        # Take browser screenshot at key stages
        if stage in ("RESEARCH", "CREATIVE", "FOCUS_GROUP", "SAVE_REPORT", "COMPLETE"):
            ss_path = SCREENSHOT_DIR / f"wave_{wave+1:02d}_{stage.lower()}_{timestamp}.png"
            try:
                await page.screenshot(path=str(ss_path))
                print(f"  Screenshot: {ss_path}")
            except Exception as e:
                print(f"  Screenshot failed: {e}")

        if stage == "COMPLETE":
            print(f"\n  Pipeline COMPLETE after {wave + 1} waves!")
            break

    # --- Final verification and screenshots ---
    final_status = get_pipeline_status(ae, session_id)
    state = final_status.get("state", {})

    # Print final results
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    print(f"  Research: {final_status['report_len']} chars")
    print(f"  Images: {final_status['num_images']}")
    print(f"  Videos: {final_status['num_videos']}")
    print(f"  Commercial: {'YES' if final_status['has_commercial'] else 'NO'}")
    print(f"  Focus Group: {'YES' if final_status['has_focus_group'] else 'NO'}")
    print(f"  Final Report: {final_status['final_report_len']} chars")
    print(f"  Total thoughts: {all_thoughts}")

    # Quality gates
    gates = {
        "research": final_status["report_len"] > 500,
        "images": final_status["num_images"] >= 1,
        "commercial_15s": final_status["has_commercial"],
        "focus_group": final_status["has_focus_group"],
        "final_pdf": final_status["final_report_len"] > 0,
        "thinking": all_thoughts > 0,
    }
    print(f"\n  QUALITY GATES:")
    for gate, passed in gates.items():
        print(f"    {gate}: {'PASS' if passed else 'FAIL'}")
    print(f"  OVERALL: {'PASS' if all(gates.values()) else 'FAIL'}")

    # Save state dump
    state_path = SCREENSHOT_DIR / f"final_state_{timestamp}.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, default=str)
    print(f"  State saved: {state_path}")

    # Now navigate to GE console to see the results visually
    print(f"\n--- Navigating to GE console to capture visual results ---")
    await _capture_ge_visual_results(page, state, timestamp)


async def _monitor_ge_pipeline(page, ae, session_id, timestamp):
    """Monitor the GE console UI during pipeline execution, taking screenshots."""
    print("\n--- Monitoring GE pipeline in browser ---")

    for wave in range(MAX_WAVES):
        status = get_pipeline_status(ae, session_id)
        stage = status["stage"]
        print(f"\n=== Wave {wave + 1} — Stage: {stage} ===")

        # Screenshot the current state
        ss_path = SCREENSHOT_DIR / f"wave_{wave+1:02d}_{stage.lower()}_{timestamp}.png"
        try:
            await page.screenshot(path=str(ss_path))
            print(f"  Screenshot: {ss_path}")
        except Exception as e:
            print(f"  Screenshot error: {e}")

        if stage == "COMPLETE":
            print("  Pipeline COMPLETE!")
            break

        # Check for thinking indicators
        try:
            thinking_els = await page.query_selector_all('[class*="thinking"], [class*="thought"], [data-thinking]')
            if thinking_els:
                print(f"  Thinking indicators visible: {len(thinking_els)}")
        except Exception:
            pass

        # Check for inline images
        try:
            images = await page.query_selector_all('img[src*="storage.googleapis.com"], img[src*="blob:"]')
            if images:
                print(f"  Inline images visible: {len(images)}")
        except Exception:
            pass

        # Wait and check for GE to update
        await page.wait_for_timeout(15_000)

        # If GE chat is idle, send "continue"
        if wave > 0:
            chat_input = None
            for sel in ['textarea', 'div[contenteditable="true"]']:
                try:
                    el = await page.wait_for_selector(sel, timeout=2_000)
                    if el and await el.is_visible():
                        chat_input = el
                        break
                except Exception:
                    continue

            if chat_input:
                await chat_input.fill("continue")
                await page.wait_for_timeout(300)
                await chat_input.press("Enter")
                print("  Sent: continue")

                # Wait for response
                await page.wait_for_timeout(30_000)

    # Final screenshots
    await _capture_ge_visual_results(page, status.get("state", {}), timestamp)


async def _capture_ge_visual_results(page, state, timestamp):
    """Take detailed screenshots of the final results in GE console."""
    # Full page screenshot
    ss_path = SCREENSHOT_DIR / f"final_full_page_{timestamp}.png"
    try:
        await page.screenshot(path=str(ss_path), full_page=True)
        print(f"  Final full page: {ss_path}")
    except Exception as e:
        print(f"  Final screenshot error: {e}")

    # Check for specific visual elements
    checks = {
        "thinking": '[class*="thinking"], [class*="thought"], [data-thought]',
        "images": 'img[src*="storage"], img[src*="blob"]',
        "video": 'video, [class*="video"]',
        "pdf": 'a[href*=".pdf"], [class*="pdf"]',
        "status_chips": '[class*="chip"], [class*="status"]',
    }
    for name, selector in checks.items():
        try:
            els = await page.query_selector_all(selector)
            print(f"  {name}: {len(els)} elements found")
        except Exception:
            print(f"  {name}: selector error")


if __name__ == "__main__":
    asyncio.run(run_browser_e2e())
