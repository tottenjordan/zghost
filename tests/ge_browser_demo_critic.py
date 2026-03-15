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
    "final_select_ad_copies": {"final_select_ad_copies": [
        {"headline": "The Sunday Reset Ritual", "body": "Transform laundry day into your weekly wellness moment. Tide Hibiscus — where plant-based power meets tropical freshness.", "cta": "Make Every Load a Ritual"},
        {"headline": "Fresh Is a Feeling", "body": "Close your eyes. Breathe in hibiscus. Open them to clothes that feel as good as they smell. Tide Fabric Softener with Hibiscus Scent.", "cta": "Feel the Difference"},
    ]},
    "final_select_vis_concepts": {"final_select_vis_concepts": [
        {"concept": "Sunday Reset Aesthetic", "description": "Warm-toned lifestyle shot of a Gen Z person in a sunlit apartment doing laundry as self-care, surrounded by hibiscus flowers and clean textiles."},
    ]},
    "img_artifact_keys": {"img_artifact_keys": [
        {"artifact_key": "product_asset_0.png", "concept_name": "demo_product_asset", "shot_type": "product_asset", "reference_type": "ASSET", "gcs_uri": "gs://zghost-media-center/demo_images_1773564237/product_asset_0.png", "auto_saved": True},
        {"artifact_key": "person_asset_0.png", "concept_name": "demo_person_asset", "shot_type": "person_asset", "reference_type": "ASSET", "gcs_uri": "gs://zghost-media-center/demo_images_1773564237/person_asset_0.png", "auto_saved": True},
        {"artifact_key": "trend_style_0.png", "concept_name": "demo_trend_style", "shot_type": "trend_style", "reference_type": "STYLE", "gcs_uri": "gs://zghost-media-center/demo_images_1773564237/trend_style_0.png", "auto_saved": True},
    ]},
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
    "gcs_folder": "demo_images_1773564237",
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
    // GE renders conversation in shadow DOMs — fall back to full page text
    let text = '';
    try {
        // Try to get text from the main conversation area
        const mainContent = document.querySelector('main') || document.querySelector('[role="main"]');
        text = (mainContent ? mainContent.innerText : document.body.innerText).toLowerCase();
    } catch(e) {
        text = document.body.innerText.toLowerCase();
    }
    // Also check all shadow roots for content
    const allText = document.body.innerText.toLowerCase();
    if (allText.length > text.length) text = allText;

    const imgs = document.querySelectorAll('img');
    const bigImgs = [];
    imgs.forEach(img => {
        if (img.width > 100 && !img.src.includes('avatar') && !img.src.includes('icon')) {
            bigImgs.push({src: img.src.substring(0, 120), w: img.width, h: img.height});
        }
    });
    const videos = document.querySelectorAll('video');
    return {
        hasResearch: text.includes('research') || text.includes('cited report') || text.includes('market intelligence'),
        hasAdCopy: text.includes('ad copy') || text.includes('ad creative') || text.includes('headline'),
        hasImages: bigImgs.length > 0,
        imageCount: bigImgs.length,
        imageSources: bigImgs.slice(0, 5),
        hasVideo: text.includes('commercial') || text.includes('video') || videos.length > 0,
        videoCount: videos.length,
        hasFocusGroup: text.includes('focus group') || text.includes('panelist'),
        hasPDF: text.includes('pdf') || text.includes('campaign brief') || text.includes('final report'),
        hasThinking: document.querySelectorAll('[class*="think"]').length > 0 || text.includes('thinking'),
        hasTrends: text.includes('trend') || text.includes('google search'),
        hasComplete: text.includes('pipeline complete') || text.includes('campaign is complete') || text.includes('report saved'),
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
        "focus_group_text": focus_group[:1000] if isinstance(focus_group, str) else "",
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

            # Click our agent — displayName is "trends2insights" in the @mention picker
            # IMPORTANT: Must NOT click "Deep Research" or "Data Agent" or the HR agent
            # (whose displayName is literally "projects/679926387543/locatio...")
            agent_clicked = False
            try:
                # Strategy 1: Click by our agent's display name "trends2insights"
                t2i_item = await page.query_selector("text=trends2insights")
                if t2i_item:
                    await t2i_item.click()
                    agent_clicked = True
                    print("  Selected agent via text match: trends2insights", flush=True)

                if not agent_clicked:
                    # Strategy 2: DOM scan for "trends2insights" text
                    all_visible = await page.query_selector_all("div, span, li, a")
                    for el in all_visible:
                        try:
                            text = await el.inner_text()
                            if "trends2insights" in text.lower():
                                bbox = await el.bounding_box()
                                if bbox and bbox["width"] > 50:
                                    await el.click()
                                    agent_clicked = True
                                    print(f"  Selected agent via DOM scan: {text[:60]}", flush=True)
                                    break
                        except Exception:
                            continue

                if not agent_clicked:
                    # Strategy 3: Type "trend" to filter the picker, then Enter
                    await page.keyboard.type("trend", delay=50)
                    await page.wait_for_timeout(1000)
                    await page.keyboard.press("Enter")
                    agent_clicked = True
                    print("  Selected agent (typed 'trend' to filter + Enter)", flush=True)

            except Exception as e:
                print(f"  Picker click error: {e}", flush=True)
                # Emergency fallback: type to filter
                await page.keyboard.type("trend", delay=50)
                await page.wait_for_timeout(1000)
                await page.keyboard.press("Enter")
                print("  Selected agent (emergency: typed 'trend' + Enter)", flush=True)

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

            # Step 4: Wait for initial agent response, then capture key moments
            # The GE conversation starts the pipeline from scratch (separate session from Phase 1).
            # We capture 3-4 key screenshots showing the agent interaction, then move to critic.
            print("  Waiting for agent response (60s)...", flush=True)
            await page.wait_for_timeout(60000)  # Wait 60s for initial response

            # Take screenshot of initial response
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            path = SS_DIR / f"ge_response_01_{ts}.png"
            await page.screenshot(path=str(path))
            screenshots.append(str(path))
            print(f"  Screenshot: {path.name}", flush=True)

            # Send "continue" to advance, wait, screenshot
            input_el = await page.query_selector("textarea, [contenteditable], [role='textbox']")
            if input_el:
                await input_el.click()
                await page.keyboard.type("continue", delay=20)
                await page.keyboard.press("Enter")
                print("  Sent 'continue'", flush=True)

            await page.wait_for_timeout(90000)  # Wait 90s for research/creative
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            path = SS_DIR / f"ge_response_02_{ts}.png"
            await page.screenshot(path=str(path))
            screenshots.append(str(path))
            print(f"  Screenshot: {path.name}", flush=True)

            # One more continue + wait
            input_el = await page.query_selector("textarea, [contenteditable], [role='textbox']")
            if input_el:
                await input_el.click()
                await page.keyboard.type("continue", delay=20)
                await page.keyboard.press("Enter")
                print("  Sent 'continue'", flush=True)

            await page.wait_for_timeout(90000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            path = SS_DIR / f"ge_response_03_{ts}.png"
            await page.screenshot(path=str(path))
            screenshots.append(str(path))
            print(f"  Screenshot: {path.name}", flush=True)

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
    from google.cloud import storage as gcs_storage

    def _download_gcs_image(gcs_uri):
        """Download image bytes from GCS URI."""
        bucket_name = gcs_uri.replace("gs://", "").split("/")[0]
        blob_name = "/".join(gcs_uri.replace("gs://", "").split("/")[1:])
        client = gcs_storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()

    print(f"\n{'#'*60}")
    print("PHASE 3: Demo Critic Evaluation")
    print(f"{'#'*60}\n", flush=True)

    # Build context about what the pipeline produced
    pipeline_summary = f"""
PIPELINE OUTPUT SUMMARY:
- Research report: {status['report_len']} chars (detailed trend analysis)
- Ad copy concepts: {status['num_ad_copies']}
- GENERATED IMAGES: {status['num_images']} (actual Imagen 4 renders with Gecko fidelity scoring)
- Videos generated: {status['num_videos']}
- {status.get('state', {}).get('commercial_duration', 8)}s Commercial video: {'YES - ' + status['commercial_uri'][:100] if status['has_commercial'] else 'NO'}
- Focus group evaluation: {'YES' if status['has_focus_group'] else 'NO'}
- Final PDF campaign brief: {status['final_report_len']} chars
- Focus group excerpt: {status['focus_group_text'][:800]}

CAMPAIGN:
- Brand: Tide
- Product: Tide Fabric Softener with Hibiscus Scent
- Target: Gen Z eco-conscious consumers
- Features: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging
"""

    # Build image/video info from state
    state = status.get("state", {})
    img_keys = state.get("img_artifact_keys", {})
    if isinstance(img_keys, dict):
        img_list = img_keys.get("img_artifact_keys", [])
    else:
        img_list = img_keys if isinstance(img_keys, list) else []
    img_info = "\n".join([
        f"  - {m.get('concept_name', '?')}: {m.get('shot_type', '?')} ({m.get('reference_type', '?')}) "
        f"Gecko: {m.get('fidelity_score', 'N/A')} | GCS: {m.get('gcs_uri', 'N/A')[:80]}"
        for m in img_list if isinstance(m, dict) and not m.get("skipped")
    ]) or "  No images generated"

    # Build parts list with screenshots
    parts = [types.Part(text=f"""You are a Demo Critic evaluating a marketing AI demo for a CEO audience.

This demo uses AI agents to automatically create a full marketing campaign. The system runs in Gemini Enterprise (Google's enterprise AI platform).

The demo has TWO components:
1. **Pipeline Output** (backend) — The actual campaign assets produced by the AI agents
2. **Gemini Enterprise UI** (screenshots) — How the user interacts with the agent via @mention in the GE chat

{pipeline_summary}

GENERATED IMAGES (with Gecko fidelity scores):
{img_info}

The generated campaign images are included below (downloaded from GCS). The screenshots show the Gemini Enterprise UI where a user @mentions the "trends2insights" agent to kick off the campaign. The agent responds with real-time status updates as it works through the pipeline.

IMPORTANT: The generated images (Imagen 4 renders) are attached INLINE below this prompt — look for them! They are the actual campaign visuals produced by the pipeline. The screenshots show the GE chat UI.

EVALUATE THIS DEMO on these criteria (score each 1-10):

1. **Visual Impact** - Look at the attached generated images. Are they professional, on-brand, and visually compelling for a Tide Hibiscus campaign?
2. **Trend Integration** - Does the research connect cultural trends to the product strategy?
3. **End-to-End Wow Factor** - Research -> Ad copy -> Images -> Video -> Focus group -> PDF report — does this flow impress?
4. **CEO Impressiveness** - Would a CEO say "I need this for my brand" based on the pipeline output quality?
5. **Completeness** - Did all stages produce meaningful output (research chars, images count, commercial, focus group, PDF)?

For each criterion, give a score and one sentence of feedback.

OVERALL SCORE (1-10) and VERDICT:
- Score >= 7: **PASS** - Demo quality is CEO-ready
- Score < 7: **FAIL** - What needs to improve

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

    # Add generated campaign images from GCS
    print(f"  img_list has {len(img_list)} entries: {[m.get('concept_name', '?') if isinstance(m, dict) else str(m)[:50] for m in img_list[:5]]}", flush=True)
    images_added = 0
    for img_meta in img_list[:5]:
        if isinstance(img_meta, dict) and not img_meta.get("skipped"):
            gcs_uri = img_meta.get("gcs_uri", "")
            print(f"  Attempting GCS download: {gcs_uri[:80]}", flush=True)
            if gcs_uri and gcs_uri.startswith("gs://"):
                try:
                    img_bytes = _download_gcs_image(gcs_uri)
                    if img_bytes:
                        parts.append(types.Part(text=f"[Generated campaign image: {img_meta.get('concept_name', '?')} — {img_meta.get('shot_type', '?')} ({img_meta.get('reference_type', '?')}) Gecko: {img_meta.get('fidelity_score', 'N/A')}]"))
                        parts.append(types.Part(
                            inline_data=types.Blob(mime_type="image/png", data=img_bytes)
                        ))
                        images_added += 1
                        print(f"  Added generated image ({len(img_bytes)} bytes): {img_meta.get('concept_name', '?')}", flush=True)
                except Exception as e:
                    print(f"  Could not load GCS image {gcs_uri}: {e}", flush=True)
    print(f"  Total GCS images added to critic: {images_added}", flush=True)

    # Add screenshot images (first 4: picker + message + initial responses)
    for ss_path in screenshots[:4]:
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
