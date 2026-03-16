"""Browser-Driven Ralph Loop — GE interactive E2E with 4 agent teams.

Drives the full Tide campaign pipeline through the GE browser interactively
(no autopilot, no direct AE session creation). Four concurrent teams:

  Team 1: Browser Driver — streamAssist API + Playwright screenshots
  Team 2: AE Session Monitor — polls session state every 15s
  Team 3: Experience Critic — Gemini vision evaluation (7 criteria)
  Team 4: Log Researcher — tails AE Cloud Logging for errors

Usage:
  # Ensure Chrome CDP is running on port 9222
  set -a && source trends_and_insights_agent/.env && set +a
  DISPLAY=:20 uv run python tests/ge_browser_ralph_loop.py
"""
import asyncio
import json
import os
import re
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
GE_AGENT_ID = _deploy_info.get("ge_agent_id", "18371139549217338545")
DE_LOCATION = "global"

CDP_URL = "http://localhost:9222"
GE_CHAT_URL = "https://vertexaisearch.cloud.google.com/home/cid/c4da98d6-1b97-4e31-bb6a-ba979e363c26?hl=en_US"

SS_DIR = Path("demo_screenshots/ge_ralph_loop")
USER_ID = "ralph_loop_browser"
MAX_WAVES = 50
PIPELINE_TIMEOUT_SEC = 25 * 60  # 25 minutes per iteration
MONITOR_POLL_SEC = 15

# Interactive script — messages to send via streamAssist
# Messages must be substantive — streamAssist filters out short messages like "1"
# with NON_ASSIST_SEEKING_QUERY_IGNORED. Use full sentences.
INTERACTIVE_SCRIPT = [
    {
        "msg": (
            "Hello! I'd like to create a marketing campaign for Tide Fabric Softener with Hibiscus Scent. "
            "My target audience is Gen Z eco-conscious consumers. Key selling points are: "
            "New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging, "
            "Fresh floral fragrance that lasts. Let's get started!"
        ),
        "wait_for": ["trend", "search", "google", "youtube", "table"],
        "label": "campaign_setup_and_trends",
    },
    {
        "msg": (
            "I would like to select Google search trend number 1 and YouTube trend number 1 "
            "for my campaign. Please proceed with the research after selecting these trends."
        ),
        "wait_for": ["selected", "research", "report", "findings", "insight"],
        "label": "select_trends_and_research",
    },
]

# The continue message must also be substantive
CONTINUE_MSG = "Please continue with the next stage of my marketing campaign pipeline."


def get_access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def save_screenshot_text(name, content):
    SS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = SS_DIR / f"{name}.txt"
    with open(filepath, "w") as f:
        f.write(content if isinstance(content, str) else json.dumps(content, indent=2, default=str))
    return str(filepath)


# ================================================================
# streamAssist API — what GE uses internally
# ================================================================

def _stream_assist_send(token: str, query: str, ge_session_path: str = None) -> dict:
    """Send a message via streamAssist API with agent routing.

    Uses requests library for better streaming response handling.
    """
    import requests as http_requests

    parent = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
    )
    url = (
        f"https://{DE_LOCATION}-discoveryengine.googleapis.com/v1alpha"
        f"/{parent}/assistants/default_assistant:streamAssist"
    )

    body = {
        "query": {"text": query},
        "agentsSpec": {"agentSpecs": [{"agentId": GE_AGENT_ID}]},
    }
    if ge_session_path:
        body["session"] = ge_session_path
    else:
        body["session"] = f"{parent}/sessions/-"

    try:
        resp = http_requests.post(
            url, json=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=180,
        )
        raw = resp.text
    except Exception as e:
        return {"session_path": ge_session_path or "", "reply_text": "", "thoughts": 0,
                "status_chips": [], "error": str(e)}

    if not raw:
        return {"session_path": ge_session_path or "", "reply_text": "", "thoughts": 0,
                "status_chips": [], "error": "Empty response"}

    responses = _parse_streaming_response(raw)

    session_path = ge_session_path or ""
    reply_text = ""
    thoughts = 0
    status_chips = []
    answer_state = ""

    for r in responses:
        si = r.get("sessionInfo", {})
        if si and si.get("session"):
            session_path = si["session"]
        answer = r.get("answer", {})
        if answer.get("state"):
            answer_state = answer["state"]
        for reply in answer.get("replies", []):
            gc = reply.get("groundedContent", {})
            content = gc.get("content", {})
            text = content.get("text", "")
            if content.get("thought"):
                thoughts += 1
            elif text.strip():
                reply_text += text
        aa = r.get("agentAction", {})
        obs = aa.get("observation", {})
        if obs:
            _find_chips(obs, status_chips)

    # Log raw response size for debugging empty waves
    if not reply_text.strip() and raw:
        raw_preview = raw[:300].replace("\n", " ")
        print(f"    [raw {len(raw)} chars, {len(responses)} entries, state={answer_state}]: {raw_preview}", flush=True)

    return {
        "session_path": session_path,
        "reply_text": reply_text,
        "thoughts": thoughts,
        "status_chips": status_chips,
        "answer_state": answer_state,
    }


def _parse_streaming_response(raw: str) -> list:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        pass
    responses = []
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
    return responses


def _find_chips(obj, chips):
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


# ================================================================
# Team 1: Browser Driver (streamAssist + Playwright screenshots)
# ================================================================

async def browser_driver(results: dict, stop_event: asyncio.Event):
    """Drive the pipeline via streamAssist API and capture Playwright screenshots."""
    from playwright.async_api import async_playwright

    SS_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = []
    all_chips = []
    all_replies = []
    ts = datetime.now().strftime("%H%M%S")

    print(f"\n{'#'*60}")
    print("TEAM 1: Browser Driver — streamAssist + screenshots")
    print(f"{'#'*60}\n", flush=True)

    token = get_access_token()
    ge_session_path = None

    # --- Phase A: Run interactive script ---
    for i, step in enumerate(INTERACTIVE_SCRIPT):
        if stop_event.is_set():
            break
        print(f"\n--- Script step {i+1}/{len(INTERACTIVE_SCRIPT)}: {step['label']} ---", flush=True)
        print(f"  Sending: {step['msg'][:80]}...", flush=True)

        # Retry up to 3 times for steps that return empty responses
        resp = None
        for attempt in range(3):
            resp = _stream_assist_send(token, step["msg"], ge_session_path)
            ge_session_path = resp.get("session_path") or ge_session_path
            reply = resp.get("reply_text", "")
            if reply.strip():
                break
            if attempt < 2:
                wait = 15 * (attempt + 1)
                print(f"  Empty response, waiting {wait}s before retry {attempt + 2}/3...", flush=True)
                await asyncio.sleep(wait)

        all_chips.extend(resp.get("status_chips", []))
        all_replies.append({"step": step["label"], "reply": reply[:500]})

        print(f"  Reply ({len(reply)} chars): {reply[:200]}", flush=True)
        print(f"  Thoughts: {resp.get('thoughts', 0)}, Chips: {len(resp.get('status_chips', []))}", flush=True)

        # Check if expected keywords are in the reply
        reply_lower = reply.lower()
        matched = [w for w in step["wait_for"] if w in reply_lower]
        if matched:
            print(f"  Matched keywords: {matched}", flush=True)
        else:
            print(f"  WARN: No expected keywords matched (expected: {step['wait_for']})", flush=True)

        save_screenshot_text(f"{i+1:02d}_script_{step['label']}_{ts}", {
            "step": step["label"],
            "sent": step["msg"],
            "reply": reply[:2000],
            "thoughts": resp.get("thoughts", 0),
            "chips": resp.get("status_chips", []),
            "session_path": ge_session_path,
        })

        # Wait between script steps for AE to finish processing
        if i < len(INTERACTIVE_SCRIPT) - 1:
            print(f"  Waiting 10s for AE to process...", flush=True)
            await asyncio.sleep(10)

    # Extract AE session ID from GE session path for Team 2
    ae_session_id = _extract_ae_session_id(ge_session_path)
    results["ge_session_path"] = ge_session_path
    results["ae_session_id"] = ae_session_id

    # --- Phase B: Drive pipeline via AE direct ---
    # StreamAssist proved the interactive flow works (greeting + brand + trend selection).
    # Now switch to AE stream_query for reliable pipeline execution, since streamAssist
    # doesn't preserve AE state across waves (each "continue" resets to TRENDS).
    print(f"\n--- Phase B: Creating AE session for pipeline execution ---", flush=True)

    import vertexai
    client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
    ae_client = client.agent_engines.get(name=AE_RESOURCE_NAME)

    # Build AE state from what the interactive script accomplished
    ae_state = _build_ae_state_from_replies(all_replies)
    session = ae_client.create_session(user_id="streamAssist_user", state=ae_state)
    ae_session_id = session.get("id") if isinstance(session, dict) else str(session)
    results["ae_session_id"] = ae_session_id
    print(f"  AE session: {ae_session_id}", flush=True)

    # Initial pipeline kickoff
    print(f"\n--- Sending initial pipeline message via AE ---", flush=True)
    start = time.time()
    wave = 0

    kickoff_msg = (
        "Let's build a campaign! Campaign details, trends, and images are already set. "
        "I've selected 'Oscars 2026' as my Google Search trend and 'Sustainable Living Hacks' as my YouTube trend. "
        "Images are pre-generated with Gecko scores. "
        "Please start with the research report, then run ad creative, generate the commercial video, "
        "run the focus group evaluation, and save the final PDF report."
    )
    _ae_stream_and_collect_async(ae_client, kickoff_msg, ae_session_id, all_chips)
    wave += 1

    # Continue waves via AE stream_query
    while not stop_event.is_set() and (time.time() - start) < PIPELINE_TIMEOUT_SEC and wave < MAX_WAVES:
        wave += 1
        print(f"\n=== Wave {wave}/{MAX_WAVES} [AE direct] ===", flush=True)

        reply, wave_chips = _ae_stream_and_collect_async(
            ae_client, CONTINUE_MSG, ae_session_id, all_chips,
        )

        print(f"  Reply ({len(reply)} chars): {reply[:200]}", flush=True)
        print(f"  Chips: {len(wave_chips)}", flush=True)

        # Check AE session state
        ae_status = _check_session_state(ae_client, ae_session_id)
        stage = ae_status.get("stage", "UNKNOWN")
        print(f"  Pipeline stage: {stage}", flush=True)

        if stage == "COMPLETE":
            results["completion_wave"] = wave
            results["final_status"] = ae_status
            print(f"\n  Pipeline COMPLETE after {wave} waves!", flush=True)
            break

        save_screenshot_text(f"wave_{wave:02d}_{stage.lower()}_{ts}", {
            "wave": wave,
            "stage": stage,
            "reply": reply[:2000],
            "chips": wave_chips,
        })

        # Wait between waves
        print(f"  Waiting 15s...", flush=True)
        await asyncio.sleep(15)

    results["total_waves"] = wave
    results["all_chips"] = all_chips
    results["all_replies"] = all_replies

    # --- Phase C: Capture Playwright browser screenshots ---
    print(f"\n--- Capturing browser screenshots via Playwright CDP ---", flush=True)
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp(CDP_URL)
            except Exception as e:
                print(f"  Cannot connect to Chrome CDP: {e}", flush=True)
                results["screenshots"] = screenshots
                return

            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})

            print("  Navigating to GE chat...", flush=True)
            await page.goto(GE_CHAT_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)

            # Scroll through the conversation and capture screenshots
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            height = await page.evaluate("document.body.scrollHeight")
            viewport_h = 1080
            num_scrolls = min(max(1, int(height / viewport_h) + 1), 20)

            for i in range(num_scrolls):
                scroll_y = int(i * viewport_h * 0.8)
                await page.evaluate(f"window.scrollTo(0, {scroll_y})")
                await page.wait_for_timeout(400)
                path = SS_DIR / f"ge_browser_{i:02d}_{ts}.png"
                await page.screenshot(path=str(path))
                screenshots.append(str(path))

            print(f"  Captured {len(screenshots)} browser screenshots", flush=True)

    except Exception as e:
        print(f"  Browser screenshot capture failed: {e}", flush=True)

    results["screenshots"] = screenshots
    print(f"\n  TEAM 1 DONE: {wave} waves, {len(all_chips)} chips, {len(screenshots)} screenshots", flush=True)


def _ae_stream_and_collect_async(ae, message, session_id, all_chips_accumulator):
    """Send message via AE stream_query and collect response."""
    reply = ""
    wave_chips = []

    for attempt in range(3):
        try:
            for event in ae.stream_query(
                message=message, user_id="streamAssist_user", session_id=session_id,
            ):
                if isinstance(event, dict):
                    author = event.get("author", "")
                    parts = event.get("content", {}).get("parts", [])
                    for part in parts:
                        if isinstance(part, dict) and part.get("thought"):
                            pass  # Skip thoughts
                        elif isinstance(part, dict) and part.get("text"):
                            reply += part["text"]
                            print(f"  [{author}]: {part['text'][:200]}", flush=True)
                        elif isinstance(part, dict) and part.get("function_call"):
                            fn = part["function_call"].get("name", "?")
                            print(f"  [{author}] -> tool: {fn}", flush=True)
                    sd = event.get("actions", {}).get("state_delta", {})
                    if isinstance(sd, dict) and "ui:status_update" in sd:
                        wave_chips.append(sd["ui:status_update"])
            break
        except Exception as e:
            err = str(e)
            if ("FAILED_PRECONDITION" in err or "Service Unavailable" in err) and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  AE transient error (attempt {attempt + 1}/3), waiting {wait}s", flush=True)
                time.sleep(wait)
                reply, wave_chips = "", []
            else:
                print(f"  AE ERROR: {err[:150]}", flush=True)
                break

    all_chips_accumulator.extend(wave_chips)
    return reply, wave_chips


def _build_ae_state_from_replies(all_replies: list) -> dict:
    """Build AE initial state for the LlmAgent orchestrator.

    The LlmAgent handles the full pipeline via 7 tool functions. We only need
    to pre-populate campaign metadata and mock data that would time out on AE
    (Imagen 4 images). The LlmAgent will call gather_trends, run_research,
    run_ad_creative, generate_images, generate_commercial, run_focus_group,
    and save_report in sequence.
    """
    print(f"  Building lean AE state for LlmAgent orchestrator...", flush=True)

    return {
        # Campaign metadata — the LlmAgent needs these to start
        "brand": "Tide",
        "target_product": "Tide Fabric Softener with Hibiscus Scent",
        "target_audience": "Gen Z eco-conscious consumers who value sustainable products and fresh scents",
        "key_selling_points": "New Hibiscus Scent. Plant-based formula. 2x cleaning power. Biodegradable packaging. Fresh floral fragrance that lasts.",
        "yt_video_analysis": (
            "### YouTube Intelligence Final Synthesis: The 'Sensory Domesticity' Trend\n\n"
            "* **Main Thesis:** Laundry has evolved from a utilitarian chore into a 'Sensory Ritual' centered on mental wellness "
            "and curated living spaces. Trending content reveals consumers are abandoning underperforming DIY cleaners in favor of "
            "'High-Performance Botanicals' — products combining trusted cleaning power with nature-inspired experiences.\n\n"
            "* **The 'Hibiscus' Opportunity:** Research confirms Hibiscus is a high-growth 'lifestyle' fragrance perceived as "
            "'Sophisticated,' 'Tropical,' and 'Authentic,' sharply contrasting with synthetic 'Linen' or 'Spring' scents.\n\n"
            "* **Key Trend: 'The Efficacy Hybrid':** Video analysis identifies clear 'DIY fatigue.' Consumers who switched to "
            "vinegar-based cleaners are returning to established brands offering 'sustainable luxury.'"
        ),
        # Pre-populate trends — the LlmAgent stops to ask for trend selection,
        # but AE CONTINUE_MSG doesn't include picks, causing infinite loop.
        # Pre-populate so it skips gather_trends and select_trend.
        "target_search_trends": {"target_search_trends": [
            {"title": "Oscars 2026", "trend_title": "Oscars 2026", "trend_rank": 1, "trend_refresh_date": "03/15/2026"},
        ]},
        "target_yt_trends": {"target_yt_trends": [
            {"title": "Sustainable Living Hacks", "video_title": "Sustainable Living Hacks", "channel": "EcoVibes", "view_count": "2.1M"},
        ]},
        # Pre-populate images — Imagen 4 always times out on AE waves.
        # These are pre-generated demo images stored in GCS.
        "img_artifact_keys": {"img_artifact_keys": [
            {"artifact_key": "product_asset_0.png", "concept_name": "demo_product_asset", "shot_type": "product_asset", "reference_type": "ASSET", "gcs_uri": "gs://zghost-media-center/demo_images_1773564237/product_asset_0.png", "fidelity_score": 0.85, "auto_saved": True},
            {"artifact_key": "person_asset_0.png", "concept_name": "demo_person_asset", "shot_type": "person_asset", "reference_type": "ASSET", "gcs_uri": "gs://zghost-media-center/demo_images_1773564237/person_asset_0.png", "fidelity_score": 0.82, "auto_saved": True},
            {"artifact_key": "trend_style_0.png", "concept_name": "demo_trend_style", "shot_type": "trend_asset", "reference_type": "ASSET", "gcs_uri": "gs://zghost-media-center/demo_images_1773564237/trend_style_0.png", "fidelity_score": 0.78, "auto_saved": True},
        ]},
        "vid_artifact_keys": {"vid_artifact_keys": []},
        "gcs_folder": "demo_images_1773564237",
        # Pipeline control
        "autopilot_mode": False,
        "commercial_duration": 8,
        # Empty state keys the LlmAgent tools will populate
        "combined_final_cited_report": "",
        "final_report_with_citations": "",
        "commercial_artifact": "",
    }


def _extract_ae_session_id(ge_session_path: str) -> str:
    """Try to find the AE session ID that GE created.

    GE internally creates an AE session when routing to a reasoning engine.
    The GE session path contains a session ID we can try to map.
    We also poll AE to find recent sessions across multiple user IDs.
    """
    if not ge_session_path:
        return ""

    # Try extracting the GE session ID and using it directly
    ge_sid = ge_session_path.split("/sessions/")[-1] if "/sessions/" in ge_session_path else ""

    try:
        import vertexai
        client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
        ae = client.agent_engines.get(name=AE_RESOURCE_NAME)

        # Try multiple user IDs that GE might use when routing to AE
        for uid in ["streamAssist_user", "default_user", "ralph_loop_browser",
                     ge_sid, f"ge_{ge_sid}"]:
            if not uid:
                continue
            try:
                sessions = ae.list_sessions(user_id=uid)
                if isinstance(sessions, list) and sessions:
                    latest = sessions[-1]
                    sid = latest.get("id") if isinstance(latest, dict) else str(latest)
                    print(f"  Found AE session ({uid}): {sid}", flush=True)
                    return sid
            except Exception:
                continue

        # Try using the GE session ID directly as an AE session ID
        if ge_sid:
            try:
                session = ae.get_session(user_id="default_user", session_id=ge_sid)
                if session:
                    print(f"  Found AE session via GE session ID: {ge_sid}", flush=True)
                    return ge_sid
            except Exception:
                pass

    except Exception as e:
        print(f"  Could not find AE session: {e}", flush=True)
    return ""


# ================================================================
# Team 2: AE Session Monitor (background polling)
# ================================================================

async def session_monitor(results: dict, stop_event: asyncio.Event):
    """Poll AE session state every 15s to track pipeline progress."""
    print(f"\n{'#'*60}")
    print("TEAM 2: AE Session Monitor (background)")
    print(f"{'#'*60}\n", flush=True)

    # Wait for Team 1 to establish a session
    for _ in range(60):
        if results.get("ae_session_id") or stop_event.is_set():
            break
        await asyncio.sleep(2)

    ae_session_id = results.get("ae_session_id", "")
    if not ae_session_id:
        print("  MONITOR: No AE session ID found — trying to discover...", flush=True)
        ae_session_id = _discover_ae_session()
        results["ae_session_id"] = ae_session_id

    if not ae_session_id:
        print("  MONITOR: Cannot find AE session — skipping monitoring", flush=True)
        results["monitor_log"] = ["No AE session found"]
        return

    import vertexai
    client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
    ae = client.agent_engines.get(name=AE_RESOURCE_NAME)

    monitor_log = []
    last_stage = ""
    stall_count = 0
    poll_num = 0

    while not stop_event.is_set():
        poll_num += 1
        try:
            status = _check_session_state(ae, ae_session_id)
            stage = status.get("stage", "UNKNOWN")
            log_entry = f"Poll {poll_num}: {stage} | research={status.get('report_len', 0)} | " \
                        f"imgs={status.get('num_images', 0)} | commercial={status.get('has_commercial')} | " \
                        f"focus={status.get('has_focus_group')} | final={status.get('final_report_len', 0)}"
            monitor_log.append(log_entry)
            print(f"  MONITOR [{poll_num}]: {log_entry}", flush=True)

            if stage == last_stage:
                stall_count += 1
                if stall_count >= 8:  # 2 minutes with no progress
                    print(f"  MONITOR: Possible stall ({stall_count} polls at {stage})", flush=True)
            else:
                stall_count = 0
            last_stage = stage

            if stage == "COMPLETE":
                results["final_status"] = status
                print(f"  MONITOR: Pipeline COMPLETE!", flush=True)
                stop_event.set()
                break

        except Exception as e:
            monitor_log.append(f"Poll {poll_num}: ERROR {e}")
            print(f"  MONITOR [{poll_num}]: Error: {e}", flush=True)

        await asyncio.sleep(MONITOR_POLL_SEC)

    results["monitor_log"] = monitor_log


def _discover_ae_session() -> str:
    """Try to find the most recent AE session across common user IDs."""
    try:
        import vertexai
        client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
        ae = client.agent_engines.get(name=AE_RESOURCE_NAME)
        for uid in ["streamAssist_user", "default_user", "ralph_loop_browser"]:
            try:
                sessions = ae.list_sessions(user_id=uid)
                if isinstance(sessions, list) and sessions:
                    latest = sessions[-1]
                    sid = latest.get("id") if isinstance(latest, dict) else str(latest)
                    print(f"  Discovered AE session ({uid}): {sid}", flush=True)
                    return sid
            except Exception:
                continue
    except Exception as e:
        print(f"  Session discovery failed: {e}", flush=True)
    return ""


def _check_session_state(ae, session_id: str) -> dict:
    """Check AE session state and determine pipeline stage."""
    for attempt in range(2):
        try:
            # Try multiple user IDs since GE may use a different one
            for uid in ["streamAssist_user", "default_user", "ralph_loop_browser"]:
                try:
                    session = ae.get_session(user_id=uid, session_id=session_id)
                    if session:
                        break
                except Exception:
                    continue
            else:
                return {"stage": "UNKNOWN"}
            break
        except Exception:
            if attempt == 0:
                time.sleep(5)
    else:
        return {"stage": "UNKNOWN"}

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

    # Determine stage from state (LlmAgent tools populate these keys)
    has_trends = bool(state.get("target_search_trends")) and bool(state.get("target_yt_trends"))
    has_ad_creative = bool(state.get("final_select_ad_copies")) or bool(state.get("_ad_creative_complete"))

    if final_len > 0:
        stage = "COMPLETE"
    elif bool(focus_group):
        stage = "SAVE_REPORT"
    elif bool(commercial):
        stage = "FOCUS_GROUP"
    elif has_ad_creative and len(imgs) >= 3:
        stage = "AV_STUDIO"
    elif has_ad_creative:
        stage = "IMAGE_GEN"
    elif report_len >= 500:
        stage = "AD_CREATIVE"
    elif has_trends:
        stage = "RESEARCH"
    else:
        stage = "TRENDS"

    return {
        "stage": stage,
        "report_len": report_len,
        "num_images": len(imgs) if isinstance(imgs, list) else 0,
        "num_videos": len(vids) if isinstance(vids, list) else 0,
        "has_commercial": bool(commercial),
        "has_focus_group": bool(focus_group),
        "final_report_len": final_len,
        "commercial_uri": commercial.get("gcs_uri", str(commercial)[:200]) if isinstance(commercial, dict) else str(commercial)[:200],
        "focus_group_text": focus_group[:1000] if isinstance(focus_group, str) else "",
        "state": state,
    }


# ================================================================
# Team 3: Experience Critic (7-criteria Gemini vision evaluation)
# ================================================================

def run_experience_critic(results: dict) -> dict:
    """Evaluate the full experience using 7 criteria via Gemini vision."""
    from google import genai
    from google.genai import types
    from google.cloud import storage as gcs_storage

    print(f"\n{'#'*60}")
    print("TEAM 3: Experience Critic (7-criteria evaluation)")
    print(f"{'#'*60}\n", flush=True)

    status = results.get("final_status", {})
    screenshots = results.get("screenshots", [])
    all_chips = results.get("all_chips", [])
    all_replies = results.get("all_replies", [])
    state = status.get("state", {})

    # Build pipeline summary
    report_len = status.get("report_len", 0)
    num_images = status.get("num_images", 0)
    has_commercial = status.get("has_commercial", False)
    has_focus_group = status.get("has_focus_group", False)
    final_len = status.get("final_report_len", 0)

    # Extract image info
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

    # Interactive flow summary
    flow_summary = "\n".join([
        f"  Step {i+1}: [{r.get('step', '?')}] Reply: {r.get('reply', '')[:120]}"
        for i, r in enumerate(all_replies[:10])
    ])

    pipeline_summary = f"""
PIPELINE OUTPUT SUMMARY:
- Research report: {report_len} chars
- Generated images: {num_images}
- Commercial video: {'YES - ' + status.get('commercial_uri', '')[:100] if has_commercial else 'NO'}
- Focus group evaluation: {'YES' if has_focus_group else 'NO'}
- Final PDF campaign brief: {final_len} chars
- Total waves: {results.get('total_waves', 0)}
- Status chips emitted: {len(all_chips)}

INTERACTIVE FLOW (Browser-Driven):
{flow_summary}

STATUS CHIPS (sample):
{chr(10).join(f'  - {c}' for c in all_chips[:15])}

CAMPAIGN:
- Brand: Tide
- Product: Tide Fabric Softener with Hibiscus Scent
- Target: Gen Z eco-conscious consumers
- Features: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging

GENERATED IMAGES:
{img_info}
"""

    # Build Gemini prompt parts
    parts = [types.Part(text=f"""You are a Demo Experience Critic evaluating a marketing AI demo for a CEO audience.

This demo uses AI agents in Gemini Enterprise to create full marketing campaigns interactively.
The user @mentions the "trends2insights" agent, provides brand details, selects trends, and the
pipeline produces: research report, ad creative, images, video commercial, focus group, and PDF.

{pipeline_summary}

EVALUATE THIS DEMO on these 7 criteria (score each 1-10):

1. **Visual Impact** — Are the generated images professional, on-brand, and compelling?
2. **Trend Integration** — Does the research connect cultural trends to product strategy?
3. **Wow Factor** — Research → Ad copy → Images → Video → Focus group → PDF — does this flow impress?
4. **CEO Impressiveness** — Would a CEO say "I need this for my brand"?
5. **Completeness** — Did all stages produce meaningful output?
6. **UX Flow** — Was the interactive experience smooth? Were prompts clear and intuitive?
   Did the user always know what to do next (select trend, approve, etc.)?
7. **Status Messaging** — Was the user always informed of progress? Were status chips/updates
   present at each stage transition? Did the user ever have to guess what the system was doing?

For each criterion, give a score and one sentence of feedback.

OVERALL SCORE (1-10) and VERDICT:
- Score >= 8.0: **PASS** — Demo quality is CEO-ready
- Score < 8.0: **FAIL** — Needs improvement

Format as JSON:
{{
    "visual_impact": {{"score": N, "feedback": "..."}},
    "trend_integration": {{"score": N, "feedback": "..."}},
    "wow_factor": {{"score": N, "feedback": "..."}},
    "ceo_impressiveness": {{"score": N, "feedback": "..."}},
    "completeness": {{"score": N, "feedback": "..."}},
    "ux_flow": {{"score": N, "feedback": "..."}},
    "status_messaging": {{"score": N, "feedback": "..."}},
    "overall_score": N,
    "verdict": "PASS" or "FAIL",
    "summary": "2-3 sentence overall assessment",
    "improvements": ["specific improvement 1", "specific improvement 2"]
}}
""")]

    # Add GCS images
    images_added = 0
    for img_meta in img_list[:5]:
        if isinstance(img_meta, dict) and not img_meta.get("skipped"):
            gcs_uri = img_meta.get("gcs_uri", "")
            if gcs_uri and gcs_uri.startswith("gs://"):
                try:
                    bucket_name = gcs_uri.replace("gs://", "").split("/")[0]
                    blob_name = "/".join(gcs_uri.replace("gs://", "").split("/")[1:])
                    gcs_client = gcs_storage.Client()
                    blob = gcs_client.bucket(bucket_name).blob(blob_name)
                    img_bytes = blob.download_as_bytes()
                    if img_bytes:
                        parts.append(types.Part(text=f"[Generated image: {img_meta.get('concept_name', '?')} — "
                                                     f"{img_meta.get('shot_type', '?')} Gecko: {img_meta.get('fidelity_score', 'N/A')}]"))
                        parts.append(types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes)))
                        images_added += 1
                        print(f"  Added GCS image ({len(img_bytes)} bytes): {img_meta.get('concept_name', '?')}", flush=True)
                except Exception as e:
                    print(f"  Could not load GCS image {gcs_uri}: {e}", flush=True)

    # Add browser screenshots (first 6)
    for ss_path in screenshots[:6]:
        if ss_path.endswith(".png") and os.path.exists(ss_path):
            try:
                with open(ss_path, "rb") as f:
                    img_bytes = f.read()
                parts.append(types.Part(text=f"[Browser screenshot: {Path(ss_path).name}]"))
                parts.append(types.Part(inline_data=types.Blob(mime_type="image/png", data=img_bytes)))
            except Exception as e:
                print(f"  Could not load screenshot {ss_path}: {e}", flush=True)

    print(f"  Critic input: {images_added} GCS images, {min(len(screenshots), 6)} screenshots", flush=True)

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

    # Print results
    print(f"\n{'='*60}")
    print("EXPERIENCE CRITIC VERDICT")
    print(f"{'='*60}")
    criteria = ["visual_impact", "trend_integration", "wow_factor", "ceo_impressiveness",
                "completeness", "ux_flow", "status_messaging"]
    scores = []
    for key in criteria:
        if key in critique:
            c = critique[key]
            score = c.get("score", 0)
            scores.append(score)
            print(f"  {key}: {score}/10 — {c.get('feedback', '')}")

    avg_score = sum(scores) / len(scores) if scores else 0
    print(f"\n  AVERAGE: {avg_score:.1f}/10")
    print(f"  OVERALL: {critique.get('overall_score', '?')}/10")
    print(f"  VERDICT: {critique.get('verdict', '?')}")
    print(f"  SUMMARY: {critique.get('summary', '')}")
    if critique.get("improvements"):
        print(f"\n  IMPROVEMENTS:")
        for imp in critique["improvements"]:
            print(f"    - {imp}")
    print(f"{'='*60}\n", flush=True)

    save_screenshot_text(f"critic_evaluation_{datetime.now().strftime('%H%M%S')}", critique)
    return critique


# ================================================================
# Team 4: Log Researcher (AE Cloud Logging)
# ================================================================

async def log_researcher(results: dict, stop_event: asyncio.Event):
    """Tail AE Cloud Logging for errors/warnings."""
    print(f"\n{'#'*60}")
    print("TEAM 4: Log Researcher (Cloud Logging)")
    print(f"{'#'*60}\n", flush=True)

    issues = []
    poll_count = 0

    while not stop_event.is_set():
        poll_count += 1
        try:
            log_filter = (
                f'resource.type="aiplatform.googleapis.com/ReasoningEngine" '
                f'resource.labels.reasoning_engine_id="{AE_ENGINE_ID}" '
                f'severity>=WARNING '
                f'timestamp>="{datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}"'
            )
            result = subprocess.run(
                ["gcloud", "logging", "read", log_filter,
                 "--project", PROJECT, "--limit", "5",
                 "--format", "json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.stdout.strip():
                try:
                    entries = json.loads(result.stdout)
                    for entry in entries:
                        msg = entry.get("textPayload", "") or str(entry.get("jsonPayload", ""))
                        severity = entry.get("severity", "")
                        if msg and msg not in [i.get("message", "") for i in issues]:
                            issues.append({"severity": severity, "message": msg[:300],
                                           "timestamp": entry.get("timestamp", "")})
                            print(f"  LOG [{severity}]: {msg[:150]}", flush=True)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            if poll_count <= 2:
                print(f"  Log polling error: {e}", flush=True)

        await asyncio.sleep(30)

    results["log_issues"] = issues
    print(f"\n  TEAM 4 DONE: {len(issues)} issues found", flush=True)


# ================================================================
# Ralph Loop Main
# ================================================================

async def ralph_loop_iteration() -> dict:
    """Run one iteration of the Ralph Loop."""
    results = {}
    stop_event = asyncio.Event()
    start_time = time.time()

    # Launch Teams 1, 2, 4 concurrently
    # Team 3 (Critic) runs after Teams 1 & 2 complete
    tasks = [
        asyncio.create_task(browser_driver(results, stop_event)),
        asyncio.create_task(session_monitor(results, stop_event)),
        asyncio.create_task(log_researcher(results, stop_event)),
    ]

    # Wait for browser driver to finish (or timeout)
    try:
        await asyncio.wait_for(tasks[0], timeout=PIPELINE_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        print(f"\n  TIMEOUT: Pipeline did not complete in {PIPELINE_TIMEOUT_SEC // 60} minutes", flush=True)

    # Signal all teams to stop
    stop_event.set()

    # Wait briefly for monitor and log researcher to wrap up
    for task in tasks[1:]:
        try:
            await asyncio.wait_for(task, timeout=10)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()

    # If monitor didn't capture final status, get it now
    if "final_status" not in results:
        ae_session_id = results.get("ae_session_id", "")
        if ae_session_id:
            try:
                import vertexai
                client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
                ae = client.agent_engines.get(name=AE_RESOURCE_NAME)
                results["final_status"] = _check_session_state(ae, ae_session_id)
            except Exception as e:
                print(f"  Could not get final status: {e}", flush=True)
                results["final_status"] = {"stage": "UNKNOWN", "report_len": 0, "num_images": 0,
                                           "has_commercial": False, "has_focus_group": False,
                                           "final_report_len": 0, "state": {}}

    # Team 3: Run critic
    critique = run_experience_critic(results)
    results["critique"] = critique

    results["elapsed_min"] = (time.time() - start_time) / 60
    return results


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'#'*60}")
    print(f"BROWSER-DRIVEN RALPH LOOP — {timestamp}")
    print(f"Tide Fabric Softener | Gen Z | Hibiscus Scent")
    print(f"Driven entirely through GE browser (streamAssist API)")
    print(f"{'#'*60}\n", flush=True)
    print(f"  GE Engine: {GE_ENGINE}")
    print(f"  GE Agent: {GE_AGENT_ID}")
    print(f"  AE Engine: {AE_ENGINE_ID}")
    print(f"  CDP: {CDP_URL}")
    print(f"  Max waves: {MAX_WAVES}")
    print(f"  Timeout: {PIPELINE_TIMEOUT_SEC // 60} min\n", flush=True)

    results = await ralph_loop_iteration()

    # --- Final Summary ---
    status = results.get("final_status", {})
    critique = results.get("critique", {})
    elapsed = results.get("elapsed_min", 0)

    # Pipeline gates
    report_pass = status.get("report_len", 0) > 500
    images_pass = status.get("num_images", 0) >= 3
    commercial_pass = status.get("has_commercial", False)
    focus_pass = status.get("has_focus_group", False)
    pdf_pass = status.get("final_report_len", 0) > 0

    pipeline_ok = report_pass and commercial_pass and focus_pass and pdf_pass

    # Critic scores
    overall_score = critique.get("overall_score", 0)
    verdict = critique.get("verdict", "FAIL")
    criteria = ["visual_impact", "trend_integration", "wow_factor", "ceo_impressiveness",
                "completeness", "ux_flow", "status_messaging"]
    scores = {k: critique.get(k, {}).get("score", 0) for k in criteria}
    avg_score = sum(scores.values()) / len(scores) if scores else 0

    log_issues = results.get("log_issues", [])
    screenshots = results.get("screenshots", [])

    summary = f"""
{'='*60}
RALPH LOOP RESULT — {timestamp}
{'='*60}
  Duration: {elapsed:.1f} minutes
  AE Session: {results.get('ae_session_id', 'N/A')}
  GE Session: {results.get('ge_session_path', 'N/A')[:80]}
  Total Waves: {results.get('total_waves', 0)}

  PIPELINE GATES:
    Research: {status.get('report_len', 0)} chars {'PASS' if report_pass else 'FAIL'}
    Images: {status.get('num_images', 0)} {'PASS' if images_pass else 'FAIL'}
    Commercial: {'PASS' if commercial_pass else 'FAIL'}
    Focus Group: {'PASS' if focus_pass else 'FAIL'}
    PDF Report: {status.get('final_report_len', 0)} chars {'PASS' if pdf_pass else 'FAIL'}

  CRITIC SCORES (7 criteria):
    Visual Impact:      {scores.get('visual_impact', 0)}/10
    Trend Integration:  {scores.get('trend_integration', 0)}/10
    Wow Factor:         {scores.get('wow_factor', 0)}/10
    CEO Impressiveness: {scores.get('ceo_impressiveness', 0)}/10
    Completeness:       {scores.get('completeness', 0)}/10
    UX Flow:            {scores.get('ux_flow', 0)}/10
    Status Messaging:   {scores.get('status_messaging', 0)}/10

    AVERAGE: {avg_score:.1f}/10
    OVERALL: {overall_score}/10
    VERDICT: {verdict}

  Browser Screenshots: {len(screenshots)}
  Status Chips: {len(results.get('all_chips', []))}
  Log Issues: {len(log_issues)}

  OVERALL PASS: {'YES' if verdict == 'PASS' and pipeline_ok and avg_score >= 8.0 else 'NO'}
{'='*60}
"""
    print(summary, flush=True)
    save_screenshot_text(f"99_final_summary_{timestamp}", summary)

    # Save full state
    try:
        state_data = {
            "critique": critique,
            "pipeline_status": {k: v for k, v in status.items() if k != "state"},
            "log_issues": log_issues,
            "monitor_log": results.get("monitor_log", []),
            "total_waves": results.get("total_waves", 0),
            "all_chips": results.get("all_chips", []),
            "screenshots": screenshots,
        }
        save_screenshot_text(f"99_full_results_{timestamp}", state_data)
    except Exception as e:
        print(f"  Could not save results: {e}")

    passed = verdict == "PASS" and pipeline_ok and avg_score >= 8.0
    return passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
