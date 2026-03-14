"""
Local autopilot E2E test for CampaignOrchestrator.

Runs against `adk web` on localhost:8000 (no AE dependency).
Uses autopilot mode with pre-populated trends state to skip interactive TRENDS
stage and go straight to RESEARCH -> CREATIVE -> FOCUS_GROUP -> SAVE_REPORT -> COMPLETE.

Pre-requisite: `adk web` must be running on port 8000:
    ./run_local.sh
    # or: uv run --env-file trends_and_insights_agent/.env adk web .

Usage:
    source trends_and_insights_agent/.env && uv run python tests/test_local_autopilot_e2e.py
"""

import json
import sys
import time
import uuid
from datetime import datetime

import requests

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

BASE_URL = "http://localhost:8000"
APP_NAME = "trends_and_insights_agent"
USER_ID = f"local-e2e-{uuid.uuid4().hex[:8]}"

# Locally there are no AE wave timeouts — pipeline should complete in very few invocations
MAX_WAVES = 10
REQUEST_TIMEOUT = 600  # 10 min per invocation (generous for local)

# Pre-populated state — Tide Fabric Softener campaign with trends already selected
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


def create_session():
    """Create a new session with pre-populated autopilot state."""
    resp = requests.post(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
        json={"state": INITIAL_STATE},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    session_id = data["id"]
    print(f"[SESSION] Created: {session_id} (user: {USER_ID})")
    return session_id


def get_session_state(session_id):
    """Fetch current session state."""
    resp = requests.get(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}",
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("state", {})


def send_message_sse(session_id, message):
    """Send a message via /run_sse and stream events.

    Returns (agent_texts, status_messages, tool_calls) where:
    - agent_texts: list of agent text responses
    - status_messages: list of ui:status_update values from state deltas
    - tool_calls: list of tool names called
    """
    print(f"\n{'='*70}")
    print(f"[USER] {message[:150]}")
    print(f"{'='*70}")

    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": message}],
        },
    }

    agent_texts = []
    status_messages = []
    tool_calls = []
    event_count = 0
    start = time.time()

    try:
        resp = requests.post(
            f"{BASE_URL}/run_sse",
            json=payload,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        buffer = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
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
                    _process_event(event, agent_texts, status_messages, tool_calls)

    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] Request timed out after {REQUEST_TIMEOUT}s")
    except requests.exceptions.ConnectionError:
        print("  [ERROR] Connection refused — is `adk web` running on port 8000?")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] {e}")

    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s] Events: {event_count}, Status msgs: {len(status_messages)}, Tools: {len(tool_calls)}")
    return agent_texts, status_messages, tool_calls


def _process_event(event, agent_texts, status_messages, tool_calls):
    """Parse a single SSE event, collecting texts, status messages, and tool calls."""
    author = event.get("author", "")
    content = event.get("content", {})
    parts = content.get("parts", []) if isinstance(content, dict) else []

    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text", "")
        is_thought = part.get("thought", False)

        if text and not is_thought:
            preview = text[:200]
            print(f"  [{author}]: {preview}{'...' if len(text) > 200 else ''}")
            agent_texts.append(text)
        elif part.get("functionCall") or part.get("function_call"):
            fc = part.get("functionCall") or part.get("function_call")
            fn = fc.get("name", "?")
            tool_calls.append(fn)
            print(f"  [{author}] -> tool: {fn}")
        elif part.get("functionResponse") or part.get("function_response"):
            fr = part.get("functionResponse") or part.get("function_response")
            fn = fr.get("name", "?")
            resp_data = fr.get("response", {})
            status = resp_data.get("status", "") if isinstance(resp_data, dict) else ""
            print(f"  [{author}] <- {fn}: {status}")

    # Extract status updates from state delta
    actions = event.get("actions", {})
    state_delta = actions.get("stateDelta", {}) or actions.get("state_delta", {})
    status_msg = state_delta.get("ui:status_update")
    if status_msg:
        status_messages.append(status_msg)
        print(f"  [STATUS] {status_msg}")


def get_pipeline_status(state):
    """Determine pipeline stage from session state."""
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


def print_status(status, wave_label=""):
    """Print pipeline status summary."""
    label = f" ({wave_label})" if wave_label else ""
    print(f"\n--- Pipeline Status{label}: {status['stage']} ---")
    print(f"  Research: {status['report_len']} chars")
    print(f"  Images: {status['num_images']}")
    print(f"  Videos: {status['num_videos']}")
    print(f"  Commercial: {'YES' if status['has_commercial'] else 'no'}")
    print(f"  Focus group: {'YES' if status['has_focus_group'] else 'no'}")
    print(f"  Final report: {status['final_report_len']} chars")


def main():
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'#'*70}")
    print(f"LOCAL AUTOPILOT E2E TEST — {timestamp}")
    print(f"Campaign: Tide Fabric Softener with Hibiscus Scent")
    print(f"Mode: autopilot, trends pre-populated")
    print(f"Server: {BASE_URL}")
    print(f"Max waves: {MAX_WAVES}")
    print(f"{'#'*70}")

    # --- Connectivity check ---
    try:
        requests.get(BASE_URL, timeout=5)
    except requests.exceptions.ConnectionError:
        print("\n[FATAL] Cannot connect to adk web on port 8000.")
        print("Start it first: ./run_local.sh")
        sys.exit(1)

    # --- Create session ---
    session_id = create_session()

    # --- Collect all status messages and tool calls across waves ---
    all_status_messages = []
    all_tool_calls = []
    all_agent_texts = []
    wave_count = 0

    # --- Initial kickoff ---
    print(f"\n{'='*70}")
    print("WAVE 0: Initial kickoff")
    print(f"{'='*70}")
    texts, statuses, tools = send_message_sse(session_id, KICKOFF_MESSAGE)
    all_agent_texts.extend(texts)
    all_status_messages.extend(statuses)
    all_tool_calls.extend(tools)

    state = get_session_state(session_id)
    status = get_pipeline_status(state)
    print_status(status, "after kickoff")

    # --- Continue loop ---
    for wave in range(1, MAX_WAVES + 1):
        if status["stage"] == "COMPLETE":
            print(f"\n  Pipeline COMPLETE after {wave} invocation(s)!")
            wave_count = wave
            break

        print(f"\n{'='*70}")
        print(f"WAVE {wave}: continue (stage: {status['stage']})")
        print(f"{'='*70}")
        texts, statuses, tools = send_message_sse(session_id, "continue")
        all_agent_texts.extend(texts)
        all_status_messages.extend(statuses)
        all_tool_calls.extend(tools)

        state = get_session_state(session_id)
        status = get_pipeline_status(state)
        print_status(status, f"wave {wave}")
        wave_count = wave + 1  # +1 for the kickoff
    else:
        print(f"\n  [WARN] Max waves ({MAX_WAVES}) reached without COMPLETE")
        wave_count = MAX_WAVES + 1

    # ===================================================================
    # RESULTS
    # ===================================================================
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60.0

    print(f"\n\n{'#'*70}")
    print(f"RESULTS — {timestamp}")
    print(f"{'#'*70}")
    print(f"  Duration: {elapsed_min:.1f} minutes")
    print(f"  Total invocations: {wave_count}")
    print(f"  Total status messages: {len(all_status_messages)}")
    print(f"  Total tool calls: {len(all_tool_calls)}")

    # --- Quality Gates ---
    print(f"\n--- Quality Gates ---")
    gates = {}

    gates["research"] = status["report_len"] > 500
    print(f"  [{'PASS' if gates['research'] else 'FAIL'}] Research report > 500 chars ({status['report_len']})")

    gates["images"] = status["num_images"] >= 1
    print(f"  [{'PASS' if gates['images'] else 'FAIL'}] At least 1 image ({status['num_images']})")

    gates["commercial"] = status["has_commercial"]
    print(f"  [{'PASS' if gates['commercial'] else 'FAIL'}] Commercial video exists")

    gates["focus_group"] = status["has_focus_group"]
    print(f"  [{'PASS' if gates['focus_group'] else 'FAIL'}] Focus group evaluation exists")

    gates["final_report"] = status["final_report_len"] > 0
    print(f"  [{'PASS' if gates['final_report'] else 'FAIL'}] Final PDF report ({status['final_report_len']} chars)")

    gates["wave_count"] = wave_count <= 5
    print(f"  [{'PASS' if gates['wave_count'] else 'WARN'}] Invocations <= 5 ({wave_count})")

    # --- Status Message Verification ---
    print(f"\n--- Status Message Verification ---")

    # 1. Dynamic messages with campaign context
    #    The orchestrator emits dynamic stage messages as event text content,
    #    while operational status updates go to state_delta. Check both.
    all_visible_text = all_status_messages + all_agent_texts
    has_campaign_context = any(
        "Tide" in msg or "Fabric Softener" in msg or "Hibiscus" in msg
        for msg in all_visible_text
    )
    gates["dynamic_status"] = has_campaign_context
    print(f"  [{'PASS' if has_campaign_context else 'FAIL'}] Dynamic messages contain campaign context (Tide/Fabric Softener)")

    # 2. Stage progression messages
    stage_keywords = {
        "RESEARCH": ["research", "Researching"],
        "CREATIVE": ["creative", "Creating", "ad copy", "visuals", "commercial"],
        "FOCUS_GROUP": ["focus group", "Focus group"],
        "SAVE_REPORT": ["report", "Report", "PDF"],
    }
    stages_seen = []
    for stage_name, keywords in stage_keywords.items():
        found = any(
            any(kw.lower() in msg.lower() for kw in keywords)
            for msg in all_status_messages
        )
        if found:
            stages_seen.append(stage_name)
    gates["stage_progression"] = len(stages_seen) >= 3
    print(f"  [{'PASS' if gates['stage_progression'] else 'FAIL'}] Stage progression messages (saw: {', '.join(stages_seen) or 'none'})")

    # 3. Operational detail messages
    operational_keywords = [
        "Generating image", "Image saved", "Veo", "operation submitted",
        "prior campaign insights", "Autopilot", "skipping",
        "Imagen", "commercial", "wave",
    ]
    operational_found = [
        kw for kw in operational_keywords
        if any(kw.lower() in msg.lower() for msg in all_status_messages)
    ]
    gates["operational_detail"] = len(operational_found) >= 2
    print(f"  [{'PASS' if gates['operational_detail'] else 'FAIL'}] Operational detail messages (found: {', '.join(operational_found) or 'none'})")

    # 4. No excessive portrait/testimonial retries in autopilot
    portrait_calls = [t for t in all_tool_calls if t in ("generate_panelist_portrait", "generate_panelist_testimonial")]
    # In autopilot, these should be intercepted by _skip_portrait_on_autopilot callback
    # They may still appear as tool calls (the callback returns a synthetic response),
    # but the key is the tool doesn't actually run (no errors/retries)
    gates["no_portrait_retries"] = len(portrait_calls) <= 6  # 3 panelists x 2 tools = 6 max
    print(f"  [{'PASS' if gates['no_portrait_retries'] else 'FAIL'}] Portrait/testimonial calls <= 6 ({len(portrait_calls)})")

    # --- All Status Messages ---
    print(f"\n--- All Status Messages ({len(all_status_messages)}) ---")
    for i, msg in enumerate(all_status_messages):
        print(f"  {i+1:3d}. {msg}")

    # --- Overall ---
    core_gates = ["research", "commercial", "focus_group", "final_report"]
    core_pass = all(gates[g] for g in core_gates)
    all_pass = all(gates.values())

    print(f"\n{'='*70}")
    if all_pass:
        print(f"OVERALL: ALL PASS")
    elif core_pass:
        print(f"OVERALL: CORE PASS (some non-critical gates failed)")
    else:
        failed = [g for g in gates if not gates[g]]
        print(f"OVERALL: FAIL (failed: {', '.join(failed)})")
    print(f"{'='*70}")

    sys.exit(0 if core_pass else 1)


if __name__ == "__main__":
    main()
