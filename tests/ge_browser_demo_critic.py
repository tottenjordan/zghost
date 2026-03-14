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
MAX_WAVES = 45

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
    "yt_video_analysis": "YouTube trend analysis: Gen Z audiences are highly engaged with sustainable product content. Key themes: eco-friendly lifestyle, plant-based products, aesthetic packaging, fresh floral scents.",
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

CAMPAIGN_MESSAGE = """Create a full marketing campaign for Tide Fabric Softener with Hibiscus Scent.

Brand: Tide
Product: Tide Fabric Softener with Hibiscus Scent
Target Audience: Gen Z eco-conscious consumers
Key Selling Points: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging

Run in autopilot mode - auto-select trend 1 for both search and YouTube trends, then proceed through the full pipeline: research, ad creative, image generation, 15s video commercial, focus group evaluation, and final PDF campaign brief."""

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
    commercial = state.get("commercial_artifact", "")
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
        "commercial_uri": commercial,
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

async def capture_ge_screenshots(session_id):
    """Open GE in browser, navigate to session, take screenshots."""
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = []

    print(f"\n{'#'*60}")
    print("PHASE 2: Capture GE browser screenshots")
    print(f"{'#'*60}\n", flush=True)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"  Cannot connect to Chrome CDP on {CDP_URL}: {e}", flush=True)
            print("  Skipping browser screenshots — using API results only", flush=True)
            return screenshots

        context = browser.contexts[0]
        page = context.pages[0]
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # Navigate to GE chat
        print("  Navigating to GE chat...", flush=True)
        await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

        ts = datetime.now().strftime("%H%M%S")

        # Take initial screenshot
        path = SS_DIR / f"ge_chat_{ts}.png"
        await page.screenshot(path=str(path))
        screenshots.append(str(path))
        print(f"  Screenshot: {path.name}", flush=True)

        # Send the campaign message in GE chat
        print("  Sending campaign message in GE...", flush=True)
        chat_sent = False
        for sel in ['div[contenteditable="true"]', 'textarea', 'input[type="text"]']:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(500)
                    await page.keyboard.type(CAMPAIGN_MESSAGE, delay=3)
                    await page.wait_for_timeout(500)
                    await page.keyboard.press("Enter")
                    chat_sent = True
                    print(f"  Message sent via {sel}", flush=True)
                    break
            except Exception:
                continue

        if not chat_sent:
            print("  Could not find chat input — taking screenshots of existing content", flush=True)

        # Monitor for content appearing (up to 30 waves, 30s each)
        print("\n  Monitoring GE for inline content...", flush=True)
        best_info = {}
        for wave in range(30):
            await page.wait_for_timeout(30000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # Take screenshot
            path = SS_DIR / f"ge_wave_{wave+1:02d}_{ts}.png"
            await page.screenshot(path=str(path))
            screenshots.append(str(path))

            # Check content
            try:
                info = await page.evaluate(CHECK_CONTENT_JS)
            except Exception:
                info = {}

            stages = []
            if info.get("hasResearch"): stages.append("RESEARCH")
            if info.get("hasAdCopy"): stages.append("AD_COPY")
            if info.get("hasImages"): stages.append(f"IMAGES({info.get('imageCount', 0)})")
            if info.get("hasVideo"): stages.append("VIDEO")
            if info.get("hasFocusGroup"): stages.append("FOCUS_GROUP")
            if info.get("hasPDF"): stages.append("PDF")

            print(f"  Wave {wave+1}: {stages} | text={info.get('textLength', 0)} chars", flush=True)
            best_info = info

            # Done when pipeline is complete
            if info.get("hasComplete") or (info.get("hasFocusGroup") and info.get("hasPDF")):
                print(f"\n  GE pipeline complete!", flush=True)
                # Scrolling screenshots for full coverage
                height = await page.evaluate("document.body.scrollHeight")
                for pct in [0, 25, 50, 75, 100]:
                    await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                    await page.wait_for_timeout(500)
                    path = SS_DIR / f"ge_FINAL_scroll{pct}_{ts}.png"
                    await page.screenshot(path=str(path))
                    screenshots.append(str(path))
                    print(f"  Final screenshot: {path.name}", flush=True)
                break

        # If pipeline didn't complete in GE, still take scrolling screenshots
        if not (best_info.get("hasComplete") or best_info.get("hasPDF")):
            height = await page.evaluate("document.body.scrollHeight")
            for pct in [0, 50, 100]:
                await page.evaluate(f"window.scrollTo(0, {int(height * pct / 100)})")
                await page.wait_for_timeout(500)
                path = SS_DIR / f"ge_partial_scroll{pct}_{ts}.png"
                await page.screenshot(path=str(path))
                screenshots.append(str(path))

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
- 15s Commercial: {'YES - ' + status['commercial_uri'][:100] if status['has_commercial'] else 'NO'}
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
    Images: {status['num_images']} {'PASS' if status['num_images'] >= 1 else 'FAIL'}
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
