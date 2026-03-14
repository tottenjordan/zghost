"""
ADK Web Browser E2E — Playwright + API hybrid test.

Runs the full Tide campaign pipeline against `adk web` on localhost:8000,
then opens the ADK web UI in a browser to take screenshots of inline artifacts.

Validates:
  - All pipeline quality gates (research, images, commercial, focus group, PDF)
  - Artifact API returns image (.png), video (.mp4), and PDF (.pdf) artifacts
  - Screenshots saved showing ADK web UI with session results

Pre-requisite: `adk web` must be running on port 8000:
    ./run_local.sh
    # or: set -a && source trends_and_insights_agent/.env && set +a && uv run adk web trends_and_insights_agent

Usage:
    source trends_and_insights_agent/.env && uv run python tests/test_adk_web_browser_e2e.py
"""

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

BASE_URL = "http://localhost:8000"
APP_NAME = "trends_and_insights_agent"
USER_ID = f"browser-e2e-{uuid.uuid4().hex[:8]}"
SS_DIR = Path("demo_screenshots/adk_web_e2e")

MAX_WAVES = 10
REQUEST_TIMEOUT = 600  # 10 min per wave

# Pre-populated autopilot state (same as test_local_autopilot_e2e.py)
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
    "yt_video_analysis": "YouTube trend analysis: Gen Z audiences are highly engaged with sustainable product content. Key themes: eco-friendly lifestyle, plant-based products, aesthetic packaging, fresh floral scents, laundry hacks that save money and the planet.",
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

KICKOFF_MESSAGE = "Run the full campaign pipeline for Tide Fabric Softener with Hibiscus Scent."


# ── API helpers ──────────────────────────────────────────────────────

def create_session():
    resp = requests.post(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
        json={"state": INITIAL_STATE},
        timeout=30,
    )
    resp.raise_for_status()
    session_id = resp.json()["id"]
    print(f"[SESSION] Created: {session_id} (user: {USER_ID})")
    return session_id


def get_session_state(session_id):
    resp = requests.get(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}",
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("state", {})


def send_message_sse(session_id, message):
    """Send a message via /run_sse, stream events, return (texts, statuses, tools)."""
    print(f"\n{'='*70}")
    print(f"[USER] {message[:150]}")
    print(f"{'='*70}")

    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
    }

    texts, statuses, tools = [], [], []
    event_count = 0
    start = time.time()

    try:
        resp = requests.post(
            f"{BASE_URL}/run_sse", json=payload, stream=True, timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        buf = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                event_count += 1
                _process_event(event, texts, statuses, tools)

    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] after {REQUEST_TIMEOUT}s")
    except requests.exceptions.ConnectionError:
        print("  [ERROR] Connection refused — is `adk web` running on port 8000?")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] {e}")

    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s] Events: {event_count}, Status: {len(statuses)}, Tools: {len(tools)}")
    return texts, statuses, tools


def _process_event(event, texts, statuses, tools):
    author = event.get("author", "")
    content = event.get("content", {})
    parts = content.get("parts", []) if isinstance(content, dict) else []

    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text", "")
        if text and not part.get("thought", False):
            print(f"  [{author}]: {text[:200]}{'...' if len(text) > 200 else ''}")
            texts.append(text)
        elif part.get("functionCall") or part.get("function_call"):
            fc = part.get("functionCall") or part.get("function_call")
            fn = fc.get("name", "?")
            tools.append(fn)
            print(f"  [{author}] -> tool: {fn}")

    actions = event.get("actions", {})
    sd = actions.get("stateDelta", {}) or actions.get("state_delta", {})
    status_msg = sd.get("ui:status_update")
    if status_msg:
        statuses.append(status_msg)
        print(f"  [STATUS] {status_msg}")


def get_pipeline_status(state):
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

    creative_attempts = state.get("_creative_pipeline_attempts", 0)
    creative_exhausted = creative_attempts >= 15

    if final_len > 0:
        stage = "COMPLETE"
    elif has_focus_group:
        stage = "SAVE_REPORT"
    elif report_len < 500:
        stage = "RESEARCH"
    elif (num_images < 1 or not has_commercial) and not creative_exhausted:
        stage = "CREATIVE"
    elif not has_focus_group:
        stage = "FOCUS_GROUP"
    else:
        stage = "SAVE_REPORT"

    return {
        "stage": stage,
        "report_len": report_len,
        "num_images": num_images,
        "num_videos": num_videos,
        "has_commercial": has_commercial,
        "has_focus_group": has_focus_group,
        "final_report_len": final_len,
    }


def list_artifacts(session_id):
    """List artifact names via ADK web artifact API."""
    resp = requests.get(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}/artifacts",
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.json()
    # Some ADK versions return 404 if no artifacts
    return []


# ── Browser (Playwright) helpers ─────────────────────────────────────

async def take_screenshot(page, name):
    ts = datetime.now().strftime("%H%M%S")
    path = SS_DIR / f"{name}_{ts}.png"
    try:
        await page.screenshot(path=str(path), full_page=True)
        print(f"  [SS] {path.name}")
    except Exception as e:
        print(f"  [SS-ERR] {name}: {e}")


async def browse_adk_web(session_id, status):
    """Open ADK web UI, navigate to the session, take screenshots."""
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        # Navigate to ADK web dev UI
        print("\n[BROWSER] Opening ADK web UI...")
        await page.goto(f"{BASE_URL}/dev-ui", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        await take_screenshot(page, "01_adk_dev_ui_home")

        # The ADK dev UI is an Angular app. Try to select the app + session.
        # The app dropdown and session list are in the sidebar.
        try:
            # Select app
            app_selector = page.locator("mat-select").first
            if await app_selector.count() > 0:
                await app_selector.click()
                await page.wait_for_timeout(1000)
                app_option = page.locator(f"mat-option:has-text('{APP_NAME}')").first
                if await app_option.count() > 0:
                    await app_option.click()
                    await page.wait_for_timeout(2000)
                    print("  Selected app")
        except Exception as e:
            print(f"  [WARN] Could not select app: {e}")

        await take_screenshot(page, "02_app_selected")

        # Try to find and click the session
        try:
            session_link = page.locator(f"text={session_id[:12]}").first
            if await session_link.count() > 0:
                await session_link.click()
                await page.wait_for_timeout(3000)
                print(f"  Selected session {session_id[:12]}...")
        except Exception as e:
            print(f"  [WARN] Could not select session: {e}")

        await take_screenshot(page, "03_session_selected")

        # Scroll through the conversation to capture inline content
        for i in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

        await take_screenshot(page, "04_conversation_scrolled")

        # Check for inline images, videos, PDFs in the DOM
        img_count = await page.locator("img").count()
        video_count = await page.locator("video").count()
        pdf_links = await page.locator('a[href*=".pdf"], a[download*=".pdf"]').count()
        print(f"  [DOM] Images: {img_count}, Videos: {video_count}, PDF links: {pdf_links}")

        # Take a final full-page screenshot
        await take_screenshot(page, "05_final_full_page")

        await browser.close()

    return {"dom_images": img_count, "dom_videos": video_count, "dom_pdf_links": pdf_links}


# ── Main ─────────────────────────────────────────────────────────────

def run_pipeline():
    """Run API-driven pipeline and return (session_id, status, all_statuses)."""
    start_time = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'#'*70}")
    print(f"ADK WEB BROWSER E2E TEST — {ts}")
    print(f"Campaign: Tide Fabric Softener with Hibiscus Scent")
    print(f"Server: {BASE_URL}")
    print(f"Max waves: {MAX_WAVES}")
    print(f"{'#'*70}")

    # Connectivity check (ADK web can be slow after code changes)
    for attempt in range(3):
        try:
            requests.get(f"{BASE_URL}/list-apps", timeout=30)
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            if attempt == 2:
                print("\n[FATAL] Cannot connect to adk web on port 8000.")
                print("Start it first: ./run_local.sh")
                sys.exit(1)
            print(f"  [RETRY] Connection attempt {attempt+1}/3 failed, waiting 10s...")
            time.sleep(10)

    session_id = create_session()
    all_statuses = []

    # Kickoff
    texts, statuses, tools = send_message_sse(session_id, KICKOFF_MESSAGE)
    all_statuses.extend(statuses)
    state = get_session_state(session_id)
    status = get_pipeline_status(state)
    print(f"\n--- After kickoff: {status['stage']} ---")

    # Wave loop
    wave_count = 0
    for wave in range(1, MAX_WAVES + 1):
        if status["stage"] == "COMPLETE":
            print(f"\n  Pipeline COMPLETE after {wave} invocation(s)!")
            wave_count = wave
            break

        print(f"\n{'='*70}")
        print(f"WAVE {wave}: continue (stage: {status['stage']})")
        print(f"{'='*70}")
        texts, statuses, tools = send_message_sse(session_id, "continue")
        all_statuses.extend(statuses)

        state = get_session_state(session_id)
        status = get_pipeline_status(state)
        print(f"\n--- Wave {wave}: {status['stage']} | research={status['report_len']} imgs={status['num_images']} commercial={'Y' if status['has_commercial'] else 'N'} fg={'Y' if status['has_focus_group'] else 'N'} final={status['final_report_len']} ---")
        wave_count = wave + 1
    else:
        print(f"\n  [WARN] Max waves ({MAX_WAVES}) reached")
        wave_count = MAX_WAVES + 1

    elapsed = (time.time() - start_time) / 60.0
    print(f"\n  Pipeline duration: {elapsed:.1f} min, {wave_count} invocations")

    return session_id, status, all_statuses, wave_count, elapsed


def print_results(status, all_statuses, wave_count, elapsed, artifacts, dom_info):
    """Print quality gates and results."""
    print(f"\n\n{'#'*70}")
    print(f"RESULTS")
    print(f"{'#'*70}")
    print(f"  Duration: {elapsed:.1f} min")
    print(f"  Total invocations: {wave_count}")
    print(f"  Status messages: {len(all_statuses)}")

    # Classify artifacts
    img_artifacts = [a for a in artifacts if str(a).endswith(".png") or str(a).endswith(".jpg")]
    vid_artifacts = [a for a in artifacts if str(a).endswith(".mp4")]
    pdf_artifacts = [a for a in artifacts if str(a).endswith(".pdf")]

    print(f"\n--- Artifacts ({len(artifacts)} total) ---")
    for a in artifacts:
        print(f"  {a}")

    # Quality gates
    print(f"\n--- Quality Gates ---")
    gates = {}

    gates["research"] = status["report_len"] > 500
    print(f"  [{'PASS' if gates['research'] else 'FAIL'}] Research > 500 chars ({status['report_len']})")

    gates["images"] = status["num_images"] >= 1
    print(f"  [{'PASS' if gates['images'] else 'FAIL'}] At least 1 image ({status['num_images']})")

    gates["commercial"] = status["has_commercial"]
    print(f"  [{'PASS' if gates['commercial'] else 'FAIL'}] Commercial video")

    gates["focus_group"] = status["has_focus_group"]
    print(f"  [{'PASS' if gates['focus_group'] else 'FAIL'}] Focus group evaluation")

    gates["final_report"] = status["final_report_len"] > 0
    print(f"  [{'PASS' if gates['final_report'] else 'FAIL'}] Final report ({status['final_report_len']} chars)")

    gates["wave_count"] = wave_count <= MAX_WAVES
    print(f"  [{'PASS' if gates['wave_count'] else 'FAIL'}] Completed in <= {MAX_WAVES} waves ({wave_count})")

    # Artifact gates
    gates["img_artifacts"] = len(img_artifacts) >= 1
    print(f"  [{'PASS' if gates['img_artifacts'] else 'FAIL'}] Image artifacts >= 1 ({len(img_artifacts)})")

    gates["vid_artifacts"] = len(vid_artifacts) >= 1
    print(f"  [{'PASS' if gates['vid_artifacts'] else 'FAIL'}] Video artifacts >= 1 ({len(vid_artifacts)})")

    gates["pdf_artifacts"] = len(pdf_artifacts) >= 1
    print(f"  [{'PASS' if gates['pdf_artifacts'] else 'FAIL'}] PDF artifacts >= 1 ({len(pdf_artifacts)})")

    # Screenshots
    ss_files = sorted(SS_DIR.glob("*.png")) if SS_DIR.exists() else []
    gates["screenshots"] = len(ss_files) >= 3
    print(f"  [{'PASS' if gates['screenshots'] else 'FAIL'}] Screenshots saved ({len(ss_files)} files in {SS_DIR})")

    # DOM info from browser
    if dom_info:
        print(f"\n--- Browser DOM ---")
        print(f"  DOM images: {dom_info.get('dom_images', 0)}")
        print(f"  DOM videos: {dom_info.get('dom_videos', 0)}")
        print(f"  DOM PDF links: {dom_info.get('dom_pdf_links', 0)}")

    # All status messages
    print(f"\n--- Status Messages ({len(all_statuses)}) ---")
    for i, msg in enumerate(all_statuses):
        print(f"  {i+1:3d}. {msg}")

    # Overall
    core_gates = ["research", "commercial", "focus_group", "final_report"]
    artifact_gates = ["img_artifacts", "vid_artifacts", "pdf_artifacts"]
    core_pass = all(gates[g] for g in core_gates)
    artifact_pass = all(gates[g] for g in artifact_gates)

    print(f"\n{'='*70}")
    if core_pass and artifact_pass:
        print("OVERALL: ALL PASS (pipeline + artifacts)")
    elif core_pass:
        failed = [g for g in artifact_gates if not gates[g]]
        print(f"OVERALL: CORE PASS, artifact gates failed: {', '.join(failed)}")
    else:
        failed = [g for g in gates if not gates[g]]
        print(f"OVERALL: FAIL ({', '.join(failed)})")
    print(f"{'='*70}")

    return core_pass


async def main():
    # Phase 1: Run pipeline via API
    session_id, status, all_statuses, wave_count, elapsed = run_pipeline()

    # Phase 2: Query artifact API
    print(f"\n{'='*70}")
    print("ARTIFACT VERIFICATION")
    print(f"{'='*70}")
    artifacts = list_artifacts(session_id)
    print(f"  Artifact API returned {len(artifacts)} artifact(s)")

    # Phase 3: Browser screenshots
    print(f"\n{'='*70}")
    print("BROWSER SCREENSHOTS")
    print(f"{'='*70}")
    dom_info = {}
    try:
        dom_info = await browse_adk_web(session_id, status)
    except Exception as e:
        print(f"  [BROWSER-ERR] {e}")
        # Non-fatal — pipeline validation is the priority

    # Phase 4: Results
    core_pass = print_results(status, all_statuses, wave_count, elapsed, artifacts, dom_info)
    sys.exit(0 if core_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
