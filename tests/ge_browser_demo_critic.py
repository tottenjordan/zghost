"""GE Browser Demo Critic — Ralph Loop E2E with visual quality evaluation.

Drives the full Tide campaign pipeline via AE API, captures GE browser
screenshots, then uses Gemini vision to critique the demo quality.
Iterates until the demo critic is pleased with flashy generated ads.

Usage:
  # Ensure Chrome CDP is running on port 9222
  set -a && source trends_and_insights_agent/.env && set +a
  DISPLAY=:20 uv run python tests/ge_browser_demo_critic.py
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

# --- Config ---
_deploy_info = {}
if os.path.exists("deployment_info.json"):
    with open("deployment_info.json") as _f:
        _deploy_info = json.load(_f)

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", _deploy_info.get("project_id", "wortz-project-352116"))
PROJECT_NUMBER = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", _deploy_info.get("project_number", "679926387543"))
AE_ENGINE_ID = _deploy_info.get("engine_id", "8788263399906607104")
AE_LOCATION = "us-central1"
AE_RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{AE_LOCATION}/reasoningEngines/{AE_ENGINE_ID}"
GE_ENGINE = _deploy_info.get("ge_engine", "gemini-enterprise-17634901_1763490144996")

CDP_URL = "http://localhost:9222"
GE_CHAT_URL = "https://vertexaisearch.cloud.google.com/home/cid/c4da98d6-1b97-4e31-bb6a-ba979e363c26?hl=en_US"

SS_DIR = Path("demo_screenshots/ge_demo_critic")
USER_ID = "demo_critic_user"
MAX_WAVES = 50

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
    "yt_video_analysis": (
        "### YouTube Intelligence Final Synthesis: The 'Sensory Domesticity' Trend\n\n"
        "* **Main Thesis:** Laundry has evolved from a utilitarian chore into a 'Sensory Ritual' centered on mental wellness "
        "and curated living spaces. Trending content reveals consumers are abandoning underperforming DIY cleaners in favor of "
        "'High-Performance Botanicals' — products combining trusted cleaning power with nature-inspired experiences.\n\n"
        "* **The 'Hibiscus' Opportunity:** Research confirms Hibiscus is a high-growth 'lifestyle' fragrance perceived as "
        "'Sophisticated,' 'Tropical,' and 'Authentic,' sharply contrasting with synthetic 'Linen' or 'Spring' scents. In "
        "'Sunday Reset' and 'Laundry ASMR' video formats, Hibiscus scent serves as a psychological signal of a fresh start.\n\n"
        "* **Key Trend: 'The Efficacy Hybrid':** Video analysis identifies clear 'DIY fatigue.' Consumers who switched to "
        "vinegar-based cleaners are returning to established brands offering 'sustainable luxury' — concentrated formulas and "
        "plant-inspired profiles. Tide Hibiscus fills this 'Efficacy Gap.'\n\n"
        "### Strategic Directives:\n"
        "1. **'Ritual-First' Marketing:** Feature product in 'Sunday Reset' and 'Home Wellness' formats\n"
        "2. **Messaging: 'Trusted Performance, Botanical Soul.'** Position as premium eco-upgrade without performance trade-offs\n"
        "3. **Visual Language:** Shift from 'detergent blue' to lush hibiscus florals and aesthetic pouring shots, "
        "aligning with 'Botanical Home' and 'Clean-Girl Aesthetic' movements"
    ),
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
    "commercial_duration": 8,
    "commercial_artifact": "",
    "campaign_guide_content": "",
    "gcs_folder": "",
}

CAMPAIGN_MESSAGE = """Create a full marketing campaign for Tide Fabric Softener with Hibiscus Scent.

Brand: Tide
Product: Tide Fabric Softener with Hibiscus Scent
Target Audience: Gen Z eco-conscious consumers
Key Selling Points: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging

Run in autopilot mode - auto-select trend 1 for both search and YouTube trends, then proceed through the full pipeline: research, ad creative, 3 reference images with Gecko fidelity scoring (product ASSET, person ASSET, trend STYLE), 8s video commercial with best Gecko-rated reference assets, focus group evaluation, and final PDF campaign brief."""

# streamAssist API config
GE_AGENT_ID = _deploy_info.get("ge_agent_id", "18371139549217338545")
DE_LOCATION = "global"

# JS helpers for GE browser
CHECK_CONTENT_JS = """() => {
    const text = document.body.innerText.toLowerCase();
    const imgs = document.querySelectorAll('img');
    const bigImgs = [];
    imgs.forEach(img => {
        if (img.width > 100 && !img.src.includes('avatar') && !img.src.includes('icon')) {
            bigImgs.push({src: img.src.substring(0, 120), w: img.width, h: img.height});
        }
    });
    const videos = document.querySelectorAll('video');
    return {
        hasResearch: text.includes('research report') || text.includes('cited report'),
        hasAdCopy: text.includes('ad copy') || text.includes('ad creative') || text.includes('headline'),
        hasImages: bigImgs.length > 0,
        imageCount: bigImgs.length,
        imageSources: bigImgs.slice(0, 5),
        hasVideo: text.includes('commercial') || videos.length > 0,
        videoCount: videos.length,
        hasFocusGroup: text.includes('focus group') || text.includes('panelist'),
        hasPDF: text.includes('pdf') || text.includes('campaign brief') || text.includes('final report'),
        hasThinking: document.querySelectorAll('[class*="think"]').length > 0,
        hasComplete: text.includes('pipeline complete') || text.includes('campaign is complete'),
        textLength: text.length,
        lastLines: text.split('\\n').filter(l => l.trim()).slice(-5).join(' | ').substring(0, 300),
    };
}"""


def save_screenshot_text(name, content):
    SS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = SS_DIR / f"{name}.txt"
    with open(filepath, "w") as f:
        f.write(content if isinstance(content, str) else json.dumps(content, indent=2, default=str))
    return str(filepath)


# ================================================================
# Part 1: Drive pipeline via AE API
# ================================================================

def get_ae_client():
    import vertexai
    client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
    return client.agent_engines.get(name=AE_RESOURCE_NAME)


def ae_stream_and_collect(ae, message, session_id):
    """Send a message via AE stream_query and collect events."""
    events = []
    agent_texts = []
    thought_count = 0

    for attempt in range(3):
        try:
            for event in ae.stream_query(
                message=message, user_id=USER_ID, session_id=session_id,
            ):
                events.append(event)
                if isinstance(event, dict):
                    author = event.get("author", "")
                    parts = event.get("content", {}).get("parts", [])
                    for part in parts:
                        if isinstance(part, dict) and part.get("thought"):
                            thought_count += 1
                        elif isinstance(part, dict) and part.get("text"):
                            text = part["text"][:300]
                            print(f"  [{author}]: {text}", flush=True)
                            agent_texts.append(f"[{author}]: {part['text']}")
                        elif isinstance(part, dict) and part.get("function_call"):
                            fn = part["function_call"].get("name", "?")
                            print(f"  [{author}] -> tool: {fn}", flush=True)
            break
        except Exception as e:
            err = str(e)
            if ("FAILED_PRECONDITION" in err or "Service Unavailable" in err) and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  AE transient error (attempt {attempt + 1}/3), waiting {wait}s", flush=True)
                time.sleep(wait)
                events, agent_texts, thought_count = [], [], 0
            else:
                print(f"  ERROR: {e}", flush=True)
                break

    print(f"  Events: {len(events)}, Thoughts: {thought_count}", flush=True)
    return events, "\n".join(agent_texts), thought_count


def get_pipeline_status(ae, session_id):
    """Check session state for pipeline progress."""
    for attempt in range(3):
        try:
            session = ae.get_session(user_id=USER_ID, session_id=session_id)
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(30 * (attempt + 1))
    else:
        return {"stage": "UNKNOWN", "state": {}}

    state = session.get("state", {}) if isinstance(session, dict) else {}
    report = state.get("combined_final_cited_report", "")
    imgs = state.get("img_artifact_keys", {})
    vids = state.get("vid_artifact_keys", {})
    final = state.get("final_report_with_citations", "")
    commercial_raw = state.get("commercial_artifact", "")
    commercial = commercial_raw
    focus_group = state.get("focus_group_evaluation", "")
    ad_copies = state.get("final_select_ad_copies", {})
    vis_concepts = state.get("final_select_vis_concepts", {})

    if isinstance(imgs, dict): imgs = imgs.get("img_artifact_keys", [])
    if isinstance(vids, dict): vids = vids.get("vid_artifact_keys", [])
    if isinstance(ad_copies, dict): ad_copies = ad_copies.get("final_select_ad_copies", [])
    if isinstance(vis_concepts, dict): vis_concepts = vis_concepts.get("final_select_vis_concepts", [])

    report_len = len(report) if isinstance(report, str) else 0
    final_len = len(final) if isinstance(final, str) else 0
    has_commercial = bool(commercial)
    has_focus_group = bool(focus_group)

    creative_attempts = state.get("_creative_pipeline_attempts", 0)
    if final_len > 0:
        stage = "COMPLETE"
    elif has_focus_group:
        stage = "SAVE_REPORT"
    elif report_len < 500:
        stage = "RESEARCH"
    elif (not has_commercial) and creative_attempts < 15:
        stage = "CREATIVE"
    elif not has_focus_group:
        stage = "FOCUS_GROUP"
    else:
        stage = "SAVE_REPORT"

    print(f"\n--- Pipeline: {stage} ---", flush=True)
    print(f"  Research: {report_len} chars | Images: {len(imgs)} | Videos: {len(vids)}", flush=True)
    print(f"  Ad copies: {len(ad_copies)} | Vis concepts: {len(vis_concepts)}", flush=True)
    print(f"  Commercial: {'YES' if has_commercial else 'no'} | Focus group: {'YES' if has_focus_group else 'no'}", flush=True)
    print(f"  Final report: {final_len} chars", flush=True)

    return {
        "stage": stage,
        "report_len": report_len,
        "num_images": len(imgs),
        "num_videos": len(vids),
        "num_ad_copies": len(ad_copies),
        "num_vis_concepts": len(vis_concepts),
        "has_commercial": has_commercial,
        "has_focus_group": has_focus_group,
        "final_report_len": final_len,
        "commercial_uri": commercial_raw.get("gcs_uri", str(commercial_raw)[:200]) if isinstance(commercial_raw, dict) else str(commercial_raw)[:200],
        "focus_group_text": focus_group[:500] if isinstance(focus_group, str) else "",
        "state": state,
    }


def run_pipeline_via_ae():
    """Drive the full pipeline via AE API. Returns final status dict."""
    print(f"\n{'#'*60}")
    print("PHASE 1: Drive pipeline via Agent Engine API")
    print(f"{'#'*60}\n", flush=True)

    ae = get_ae_client()
    session = ae.create_session(user_id=USER_ID, state=INITIAL_STATE)
    session_id = session.get("id") if isinstance(session, dict) else str(session)
    print(f"Session: {session_id}", flush=True)

    # Initial kickoff
    events, texts, thoughts = ae_stream_and_collect(
        ae, "Run the full campaign pipeline for Tide Fabric Softener with Hibiscus Scent.", session_id,
    )
    status = get_pipeline_status(ae, session_id)

    for wave in range(MAX_WAVES):
        if status["stage"] == "COMPLETE":
            print(f"\n  Pipeline COMPLETE after {wave + 1} wave(s)!", flush=True)
            break
        print(f"\n=== Wave {wave + 2}/{MAX_WAVES + 1} ({status['stage']}) ===", flush=True)
        events, texts, thoughts = ae_stream_and_collect(ae, "continue", session_id)
        status = get_pipeline_status(ae, session_id)

    return status, session_id


# ================================================================
# Part 2: Capture GE browser screenshots
# ================================================================

def _stream_assist_send(token: str, query: str, ge_session_path: str = None) -> dict:
    """Send a message via streamAssist API with proper agent routing."""
    import requests as http_requests

    parent = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
    )
    url = f"https://{DE_LOCATION}-discoveryengine.googleapis.com/v1alpha/{parent}/assistants/default_assistant:streamAssist"

    body = {
        "query": {"text": query},
        "agentsSpec": {"agentSpecs": [{"agentId": GE_AGENT_ID}]},
    }
    if ge_session_path:
        body["session"] = ge_session_path
    else:
        body["session"] = f"{parent}/sessions/-"

    resp = http_requests.post(
        url, json=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=180,
    )

    raw = resp.text
    # Parse streaming JSON response
    responses = []
    try:
        parsed = json.loads(raw)
        responses = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        for line in raw.strip().split("\n"):
            line = line.strip().rstrip(",")
            if line.startswith("["):
                line = line[1:]
            if line.endswith("]"):
                line = line[:-1]
            if not line:
                continue
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    # Extract session ID and reply text
    session_path = ""
    reply_text = ""
    thoughts = 0
    status_chips = []
    for r in responses:
        si = r.get("sessionInfo", {})
        if si and si.get("session"):
            session_path = si["session"]
        answer = r.get("answer", {})
        for reply in answer.get("replies", []):
            gc = reply.get("groundedContent", {})
            content = gc.get("content", {})
            text = content.get("text", "")
            if content.get("thought"):
                thoughts += 1
            elif text.strip():
                reply_text += text
        # Check for status chips in agent actions
        aa = r.get("agentAction", {})
        obs = aa.get("observation", {})
        if obs:
            _find_chips(obs, status_chips)

    return {
        "session_path": session_path,
        "reply_text": reply_text,
        "thoughts": thoughts,
        "status_chips": status_chips,
    }


def _find_chips(obj, chips):
    """Recursively find status chips in agent output."""
    if isinstance(obj, dict):
        if "ui:status_update" in obj:
            chips.append(obj["ui:status_update"])
        sd = obj.get("state_delta", {})
        if isinstance(sd, dict) and "ui:status_update" in sd:
            chips.append(sd["ui:status_update"])
        for v in obj.values():
            if isinstance(v, (dict, list)):
                _find_chips(v, chips)
    elif isinstance(obj, list):
        for item in obj:
            _find_chips(item, chips)


async def capture_ge_screenshots(session_id):
    """Drive pipeline in GE browser via @mention picker and capture screenshots.

    Types @mention in the GE chat input to route to our agent, sends the
    campaign message, then takes screenshots as the conversation progresses.
    Falls back to streamAssist API if browser input fails.
    """
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = []

    print(f"\n{'#'*60}")
    print("PHASE 2: GE Browser — @mention + screenshots")
    print(f"{'#'*60}\n", flush=True)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"  Cannot connect to Chrome CDP on {CDP_URL}: {e}", flush=True)
            return screenshots

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # Navigate to GE chat home
        print("  Navigating to GE chat...", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        ts = datetime.now().strftime("%H%M%S")

        # Step 1: Type @ to trigger agent picker, select our agent
        print("  Triggering @mention picker...", flush=True)
        input_el = await page.query_selector("textarea, [contenteditable], [role='textbox']")
        if not input_el:
            # Fallback: click on the placeholder text
            await page.click("text=Ask anything", timeout=5000)
            await page.wait_for_timeout(500)
            input_el = await page.query_selector("textarea, [contenteditable], [role='textbox']")

        if input_el:
            await input_el.click()
            await page.wait_for_timeout(300)
            await input_el.type("@", delay=100)
            await page.wait_for_timeout(2000)

            # Take screenshot of the @mention picker
            path = SS_DIR / f"ge_01_mention_picker_{ts}.png"
            await page.screenshot(path=str(path))
            screenshots.append(str(path))
            print(f"  Screenshot: {path.name}", flush=True)

            # Click our agent (the projects/679926387543/locatio... entry)
            agent_clicked = False
            try:
                # Look for the agent with our project number in the picker
                picker_items = await page.query_selector_all("[role='option'], [role='listbox'] > *, [class*='option'], [class*='item']")
                for item in picker_items:
                    text = await item.inner_text()
                    if "679926387543" in text or "projects/" in text:
                        await item.click()
                        agent_clicked = True
                        print(f"  Selected agent: {text[:60]}", flush=True)
                        break

                if not agent_clicked:
                    # Try clicking the third item (index 2) in the picker
                    all_items = await page.query_selector_all("[role='option'], li, [class*='menu-item']")
                    if len(all_items) >= 3:
                        await all_items[2].click()
                        agent_clicked = True
                        print("  Selected agent (3rd picker item)", flush=True)
                    elif all_items:
                        await all_items[-1].click()
                        agent_clicked = True
                        print("  Selected agent (last picker item)", flush=True)
            except Exception as e:
                print(f"  Picker click error: {e}", flush=True)

            if not agent_clicked:
                # Last resort: press down arrow keys + Enter
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                print("  Selected agent (keyboard navigation)", flush=True)

            await page.wait_for_timeout(1000)

            # Step 2: Type the campaign message
            short_msg = (
                "Create a full marketing campaign for Tide Fabric Softener "
                "with Hibiscus Scent. Target: Gen Z. Key: New Hibiscus Scent, "
                "Plant-based formula, Biodegradable packaging. "
                "Run full pipeline: research, 3 reference images with Gecko scoring, "
                "8s video commercial, focus group, and PDF report."
            )
            await page.keyboard.type(short_msg, delay=10)
            await page.wait_for_timeout(500)

            # Take screenshot of the typed message
            path = SS_DIR / f"ge_02_message_typed_{ts}.png"
            await page.screenshot(path=str(path))
            screenshots.append(str(path))
            print(f"  Screenshot: {path.name}", flush=True)

            # Step 3: Submit the message
            await page.keyboard.press("Enter")
            print("  Message submitted!", flush=True)
            await page.wait_for_timeout(3000)

            # Step 4: Monitor the conversation — take screenshots as it progresses
            prev_text_len = 0
            stale_count = 0
            for wave in range(MAX_WAVES):
                await page.wait_for_timeout(15000)  # Wait 15s between checks

                # Scroll to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)

                # Check content
                try:
                    info = await page.evaluate(CHECK_CONTENT_JS)
                    text_len = info.get("textLength", 0)
                    stages = []
                    if info.get("hasResearch"): stages.append("RESEARCH")
                    if info.get("hasAdCopy"): stages.append("AD_COPY")
                    if info.get("hasImages"): stages.append(f"IMAGES({info.get('imageCount', 0)})")
                    if info.get("hasVideo"): stages.append("VIDEO")
                    if info.get("hasFocusGroup"): stages.append("FOCUS_GROUP")
                    if info.get("hasPDF"): stages.append("PDF")
                    if info.get("hasComplete"): stages.append("COMPLETE")
                    print(f"  [Wave {wave+1}] {stages} | text={text_len} chars", flush=True)

                    # Take screenshot if content changed
                    if text_len > prev_text_len + 50 or wave % 3 == 0:
                        path = SS_DIR / f"ge_wave_{wave+1:02d}_{ts}.png"
                        await page.screenshot(path=str(path))
                        screenshots.append(str(path))
                        print(f"  Screenshot: {path.name}", flush=True)
                        stale_count = 0
                    else:
                        stale_count += 1

                    prev_text_len = text_len

                    # Check if pipeline is complete (via AE status)
                    try:
                        status = get_pipeline_status(get_ae_client(), session_id)
                        if status["stage"] == "COMPLETE":
                            print(f"\n  Pipeline COMPLETE at wave {wave + 1}!", flush=True)
                            break
                    except Exception:
                        pass

                    # Also check browser for completion
                    if info.get("hasComplete") or info.get("hasPDF"):
                        print(f"\n  Pipeline complete detected in browser!", flush=True)
                        break

                    # If content is stale for 5+ checks, try sending "continue"
                    if stale_count >= 5:
                        print(f"  Content stale for {stale_count} checks, sending 'continue'...", flush=True)
                        input_el = await page.query_selector("textarea, [contenteditable], [role='textbox']")
                        if input_el:
                            await input_el.click()
                            await page.keyboard.type("continue", delay=20)
                            await page.keyboard.press("Enter")
                            stale_count = 0

                except Exception as e:
                    print(f"  [Wave {wave+1}] Content check error: {e}", flush=True)

        else:
            print("  ERROR: Could not find GE input element!", flush=True)

        # Final scrolling screenshots of the full conversation
        print("\n  Taking final scrolling screenshots...", flush=True)
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        height = await page.evaluate("document.body.scrollHeight")
        viewport_h = 1080
        num_scrolls = max(1, int(height / viewport_h) + 1)
        num_scrolls = min(num_scrolls, 15)

        for i in range(num_scrolls):
            scroll_y = int(i * viewport_h * 0.8)
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await page.wait_for_timeout(500)
            path = SS_DIR / f"ge_FINAL_{i:02d}_{ts}.png"
            await page.screenshot(path=str(path))
            screenshots.append(str(path))
            print(f"  Final screenshot {i+1}/{num_scrolls}: {path.name}", flush=True)

    return screenshots


# ================================================================
# Part 3: Demo Critic — Gemini vision evaluation
# ================================================================

def run_demo_critic(status, screenshots):
    """Use Gemini to evaluate the demo quality from pipeline output and screenshots.

    Returns a dict with score (1-10), verdict (PASS/FAIL), and feedback.
    The critic evaluates from a CEO's perspective: are the ads flashy enough?
    Does the demo show off trend-driven creative generation impressively?
    """
    from google import genai
    from google.genai import types

    print(f"\n{'#'*60}")
    print("PHASE 3: Demo Critic Evaluation")
    print(f"{'#'*60}\n", flush=True)

    # Build context about what the pipeline produced
    pipeline_summary = f"""
PIPELINE OUTPUT SUMMARY:
- Research report: {status['report_len']} chars
- Ad copies generated: {status['num_ad_copies']}
- Visual concepts: {status['num_vis_concepts']}
- Campaign images: {status['num_images']}
- Videos: {status['num_videos']}
- {status.get('state', {}).get('commercial_duration', 8)}s Commercial: {'YES - ' + status['commercial_uri'][:100] if status['has_commercial'] else 'NO'}
- Focus group evaluation: {'YES' if status['has_focus_group'] else 'NO'}
- Final PDF report: {status['final_report_len']} chars
- Focus group excerpt: {status['focus_group_text'][:300]}

CAMPAIGN:
- Brand: Tide
- Product: Tide Fabric Softener with Hibiscus Scent
- Target: Gen Z eco-conscious consumers
- Features: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging
"""

    # Build parts list with screenshots
    parts = [types.Part(text=f"""You are a Demo Critic evaluating a marketing AI demo for a CEO audience.

This demo uses AI agents to automatically create a full marketing campaign from trending topics.
The pipeline goes: Trend Discovery -> Research -> Ad Creative -> Image Generation -> Video Commercial -> Focus Group -> PDF Report.

{pipeline_summary}

{'I am also showing you ' + str(len(screenshots)) + ' browser screenshots from the Gemini Enterprise UI.' if screenshots else 'No browser screenshots were captured.'}

EVALUATE THIS DEMO on these criteria (score each 1-10):

1. **Visual Impact** - Are there flashy, impressive generated images? Do they look professional and on-brand for Tide?
2. **Trend Integration** - Does the creative clearly connect to current trends (sustainable laundry, eco cleaning)?
3. **End-to-End Wow Factor** - Does seeing research -> ads -> images -> video -> focus group -> report feel like magic?
4. **CEO Impressiveness** - Would a CEO watching this demo say "wow, I need this for my brand"?
5. **Completeness** - Did all pipeline stages produce meaningful output (not errors or empty)?

For each criterion, give a score and one sentence of feedback.

Then give an OVERALL SCORE (1-10) and a VERDICT:
- Score >= 7: **PASS** - Demo is impressive enough to show a CEO
- Score < 7: **FAIL** - Explain exactly what needs to improve

Format as JSON:
{{
    "visual_impact": {{"score": N, "feedback": "..."}},
    "trend_integration": {{"score": N, "feedback": "..."}},
    "wow_factor": {{"score": N, "feedback": "..."}},
    "ceo_impressiveness": {{"score": N, "feedback": "..."}},
    "completeness": {{"score": N, "feedback": "..."}},
    "overall_score": N,
    "verdict": "PASS" or "FAIL",
    "summary": "2-3 sentence overall assessment",
    "improvements": ["specific improvement 1", "specific improvement 2"]
}}
""")]

    # Add screenshot images
    for ss_path in screenshots[-10:]:  # Last 10 screenshots (most recent / final)
        if ss_path.endswith(".png") and os.path.exists(ss_path):
            try:
                with open(ss_path, "rb") as f:
                    img_bytes = f.read()
                parts.append(types.Part(
                    inline_data=types.Blob(mime_type="image/png", data=img_bytes)
                ))
            except Exception as e:
                print(f"  Could not load screenshot {ss_path}: {e}", flush=True)

    client = genai.Client(vertexai=True)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=parts,
        config=types.GenerateContentConfig(
            temperature=0.5,
            response_mime_type="application/json",
        ),
    )

    try:
        critique = json.loads(response.text)
    except json.JSONDecodeError:
        print(f"  Critic response not valid JSON: {response.text[:300]}", flush=True)
        critique = {"overall_score": 0, "verdict": "FAIL", "summary": "Could not parse critic response"}

    # Print critique
    print(f"\n{'='*60}")
    print("DEMO CRITIC VERDICT")
    print(f"{'='*60}")
    for key in ["visual_impact", "trend_integration", "wow_factor", "ceo_impressiveness", "completeness"]:
        if key in critique:
            c = critique[key]
            print(f"  {key}: {c.get('score', '?')}/10 — {c.get('feedback', '')}")
    print(f"\n  OVERALL: {critique.get('overall_score', '?')}/10")
    print(f"  VERDICT: {critique.get('verdict', '?')}")
    print(f"  SUMMARY: {critique.get('summary', '')}")
    if critique.get("improvements"):
        print(f"\n  IMPROVEMENTS NEEDED:")
        for imp in critique["improvements"]:
            print(f"    - {imp}")
    print(f"{'='*60}\n", flush=True)

    save_screenshot_text(f"critic_evaluation_{datetime.now().strftime('%H%M%S')}", critique)
    return critique


# ================================================================
# Part 4: Main — Ralph Loop
# ================================================================

async def main():
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'#'*60}")
    print(f"GE BROWSER DEMO CRITIC — RALPH LOOP")
    print(f"Tide Fabric Softener | Gen Z | Hibiscus Scent")
    print(f"{'#'*60}\n", flush=True)

    # Phase 1: Run pipeline via AE API
    status, session_id = run_pipeline_via_ae()

    # Quick quality gate check
    pipeline_ok = (
        status["report_len"] > 500
        and status["has_commercial"]
        and status["has_focus_group"]
        and status["final_report_len"] > 0
    )

    if not pipeline_ok:
        print(f"\n  PIPELINE INCOMPLETE — quality gates not met", flush=True)
        print(f"  Research: {status['report_len']} chars (need >500)")
        print(f"  Commercial: {status['has_commercial']}")
        print(f"  Focus group: {status['has_focus_group']}")
        print(f"  Final report: {status['final_report_len']} chars")
        print(f"\n  Proceeding to browser capture anyway...", flush=True)

    # Phase 2: Capture GE browser screenshots
    screenshots = await capture_ge_screenshots(session_id)

    # Phase 3: Demo critic evaluation
    critique = run_demo_critic(status, screenshots)

    # Final summary
    elapsed = (time.time() - start_time) / 60
    overall = critique.get("overall_score", 0)
    verdict = critique.get("verdict", "FAIL")

    summary = f"""
{'='*60}
RALPH LOOP RESULT — {timestamp}
{'='*60}
  Duration: {elapsed:.1f} minutes
  Session: {session_id}

  Pipeline Gates:
    Research: {status['report_len']} chars {'PASS' if status['report_len'] > 500 else 'FAIL'}
    Images: {status['num_images']} {'PASS' if status['num_images'] >= 3 else 'FAIL'}
    Commercial: {'PASS' if status['has_commercial'] else 'FAIL'}
    Focus Group: {'PASS' if status['has_focus_group'] else 'FAIL'}
    PDF Report: {'PASS' if status['final_report_len'] > 0 else 'FAIL'}

  Demo Critic: {overall}/10 — {verdict}
  Browser Screenshots: {len(screenshots)}

  OVERALL: {'PASS' if verdict == 'PASS' and pipeline_ok else 'FAIL'}
{'='*60}
"""
    print(summary, flush=True)
    save_screenshot_text(f"99_final_summary_{timestamp}", summary)

    # Save full state
    try:
        state_json = json.dumps(status.get("state", {}), indent=2, default=str)
        save_screenshot_text(f"99_full_state_{timestamp}", state_json[:50000])
    except Exception as e:
        print(f"  Could not save state: {e}")

    return verdict == "PASS" and pipeline_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
