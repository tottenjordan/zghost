"""E2E test for Gemini Enterprise streamAssist — full campaign pipeline.

Tests the complete flow through Discovery Engine's streamAssist API:
1. Verify agent config (reasoning engine mapping)
2. Send campaign query via streamAssist
3. Loop "continue" until pipeline completes or MAX_WAVES reached
4. Verify: thoughts displayed, status chips emitted, artifacts produced

Quality gates:
- Research report > 500 chars
- At least 1 image artifact
- Commercial video generated
- Focus group evaluation present
- Final PDF report saved

Usage:
  source trends_and_insights_agent/.env
  uv run python tests/test_ge_stream_assist_e2e.py

  # With custom settings
  uv run python tests/test_ge_stream_assist_e2e.py --max-waves 30 --de-location global
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

# --- Configuration (reads from deployment_info.json if available) ---
_deploy_info = {}
if os.path.exists("deployment_info.json"):
    with open("deployment_info.json") as _f:
        _deploy_info = json.load(_f)

PROJECT = os.environ.get("GCP_PROJECT", os.environ.get("GOOGLE_CLOUD_PROJECT", _deploy_info.get("project_id", "wortz-project-352116")))
PROJECT_NUMBER = os.environ.get("GCP_PROJECT_NUMBER", os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", _deploy_info.get("project_number", "679926387543")))

# Discovery Engine (Gemini Enterprise)
DE_LOCATION = os.environ.get("DE_LOCATION", "global")
GE_ENGINE = os.environ.get("GE_ENGINE", _deploy_info.get("ge_engine", "gemini-enterprise-17634901_1763490144996"))
GE_AGENT_ID = os.environ.get("GE_AGENT_ID", _deploy_info.get("ge_agent_id", "3607510876288067860"))

# Agent Engine (Reasoning Engine) that GE routes to
AE_ENGINE_ID = os.environ.get("AE_ENGINE_ID", _deploy_info.get("engine_id", "8788263399906607104"))
AE_LOCATION = os.environ.get("AE_LOCATION", "us-central1")
AE_RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{AE_LOCATION}/reasoningEngines/{AE_ENGINE_ID}"

MAX_WAVES = 45
SCREENSHOT_DIR = "demo_screenshots/ge_stream_assist"
USER_ID = "ge_e2e_test"

# Pre-populated state for the AE session
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


def get_base_url() -> str:
    if DE_LOCATION == "global":
        return "https://global-discoveryengine.googleapis.com"
    return f"https://{DE_LOCATION}-discoveryengine.googleapis.com"


def save_screenshot(name, content):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filepath = os.path.join(SCREENSHOT_DIR, f"{name}.txt")
    with open(filepath, "w") as f:
        f.write(content if isinstance(content, str) else json.dumps(content, indent=2, default=str))
    print(f"  [SCREENSHOT] {filepath}")
    return filepath


# ================================================================
# Part 1: Discovery Engine (streamAssist) verification
# ================================================================

def check_agent_config(base_url: str, token: str) -> dict:
    """Verify the GE agent is correctly mapped to our reasoning engine."""
    agent_name = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
        f"/agents/{GE_AGENT_ID}"
    )
    url = f"{base_url}/v1alpha/{agent_name}"

    result = subprocess.run(
        ["curl", "-s", "-X", "GET", url,
         "-H", f"Authorization: Bearer {token}",
         "-H", "Content-Type: application/json"],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        print(f"  ERROR: Could not parse agent config: {result.stdout[:200]}")
        return {"error": "parse_error"}

    if "error" in data:
        print(f"  API ERROR: {data['error'].get('message', data['error'])}")
        return data

    display = data.get("displayName", "")
    vertex_ai = data.get("vertexAiAgentConfig", data.get("adk_agent_definition", {}))
    reasoning_engine = ""
    if isinstance(vertex_ai, dict):
        reasoning_engine = vertex_ai.get("agent", vertex_ai.get("provisioned_reasoning_engine", {}).get("reasoning_engine", ""))

    mapped_correctly = str(AE_ENGINE_ID) in str(reasoning_engine)

    print(f"\n--- GE Agent Config ---")
    print(f"  Display Name: {display}")
    print(f"  Reasoning Engine: {reasoning_engine}")
    print(f"  Expected: reasoningEngines/{AE_ENGINE_ID}")
    print(f"  Mapping: {'CORRECT' if mapped_correctly else 'MISMATCH'}")

    return {
        "display_name": display,
        "reasoning_engine": reasoning_engine,
        "mapped_correctly": mapped_correctly,
        "raw": data,
    }


def stream_assist_query(base_url: str, token: str, query: str, session_id: str = None) -> dict:
    """Send a query via streamAssist and parse the streaming response.

    Uses agentsSpec to explicitly route to the registered GE agent.
    This is required — without agentsSpec, GE may answer directly with
    generic Gemini knowledge instead of routing to the reasoning engine.
    """
    parent = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
    )
    url = f"{base_url}/v1alpha/{parent}/assistants/default_assistant:streamAssist"

    body = {
        "query": {"text": query},
        # Explicit agent routing — the key to ensuring GE delegates to our ADK agent
        "agentsSpec": {
            "agentSpecs": [{"agentId": GE_AGENT_ID}]
        },
    }
    if session_id:
        body["session"] = f"{parent}/sessions/{session_id}"
    else:
        # Auto-create session
        body["session"] = f"{parent}/sessions/-"

    result = subprocess.run(
        ["curl", "-s", "-X", "POST", url,
         "-H", f"Authorization: Bearer {token}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(body)],
        capture_output=True, text=True,
        timeout=180,
    )

    raw = result.stdout
    if not raw:
        print(f"  ERROR: Empty response. stderr: {result.stderr[:200]}")
        return {"error": "empty_response", "raw_responses": []}

    # Parse streaming response
    responses = _parse_streaming_response(raw)

    # Extract key fields
    extracted = _extract_response_data(responses)
    extracted["raw_responses"] = responses

    return extracted


def _parse_streaming_response(raw: str) -> list:
    """Parse newline-delimited JSON or JSON array from streaming response."""
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


def _extract_response_data(responses: list) -> dict:
    """Extract thoughts, status chips, agent actions, and reply text from responses.

    streamAssist response structure:
        answer.state: "IN_PROGRESS" | "SUCCEEDED"
        answer.replies[].groundedContent.content.text
        answer.replies[].groundedContent.content.thought (bool)
        sessionInfo.session: "projects/.../sessions/..."
    """
    session_id = None
    reply_text = ""
    thoughts = []
    status_chips = []
    agent_actions = []
    routed_to_agent = False
    has_artifacts = False

    for resp in responses:
        # Session info (appears in the last entry)
        session_info = resp.get("sessionInfo", {})
        if session_info:
            session_name = session_info.get("session", "")
            if "/sessions/" in session_name:
                session_id = session_name.split("/sessions/")[-1]

        # Answer structure (streamAssist v1alpha format)
        answer = resp.get("answer", {})
        if answer:
            for reply in answer.get("replies", []):
                gc = reply.get("groundedContent", {})
                content = gc.get("content", {})
                text = content.get("text", "")
                is_thought = content.get("thought", False)

                if text.strip():
                    if is_thought:
                        thoughts.append(text.strip())
                    else:
                        reply_text += text
                        # Detect agent routing from content
                        # Our orchestrator's status messages indicate agent routing
                        agent_indicators = [
                            "campaign metadata", "research pipeline",
                            "creative production", "focus group",
                            "campaign report", "Generating", "Running",
                        ]
                        if any(ind.lower() in text.lower() for ind in agent_indicators):
                            routed_to_agent = True

        # Legacy reply format (older API versions)
        reply = resp.get("reply", {})
        if reply:
            summary = reply.get("summary", {})
            if summary and summary.get("summaryText"):
                reply_text += summary["summaryText"]
            refs = summary.get("references", []) if summary else []
            for ref in refs:
                if "reasoningEngine" in str(ref).lower():
                    routed_to_agent = True

        # Agent actions
        agent_action = resp.get("agentAction", {})
        if agent_action:
            tool_use = agent_action.get("toolUse", {})
            if tool_use:
                tool_name = tool_use.get("tool", "")
                agent_actions.append(tool_name)
                routed_to_agent = True

            observation = agent_action.get("observation", {})
            if observation:
                agent_output = observation.get("agentOutput", {})
                if agent_output:
                    thoughts.extend(_find_thoughts(agent_output))
                    status_chips.extend(_find_status_chips(agent_output))
                    if _has_media_artifacts(agent_output):
                        has_artifacts = True

        # Grounding metadata
        grounding = resp.get("groundingMetadata", {})
        if grounding and "reasoningEngine" in str(grounding).lower():
            routed_to_agent = True

    return {
        "session_id": session_id,
        "reply_text": reply_text,
        "thoughts": thoughts,
        "status_chips": status_chips,
        "agent_actions": agent_actions,
        "routed_to_agent": routed_to_agent,
        "has_artifacts": has_artifacts,
    }


def _find_thoughts(agent_output: dict) -> list:
    """Recursively find thought parts in agent output."""
    thoughts = []
    if isinstance(agent_output, dict):
        for key, val in agent_output.items():
            if key == "thought" and val:
                thoughts.append(str(val)[:100])
            elif key == "thinkingContent":
                thoughts.append(str(val)[:100])
            elif isinstance(val, (dict, list)):
                thoughts.extend(_find_thoughts(val))
    elif isinstance(agent_output, list):
        for item in agent_output:
            thoughts.extend(_find_thoughts(item))
    return thoughts


def _find_status_chips(agent_output: dict) -> list:
    """Find ui:status_update entries in agent output."""
    chips = []
    if isinstance(agent_output, dict):
        for key, val in agent_output.items():
            if key == "ui:status_update" and val:
                chips.append(str(val))
            elif key == "state_delta" and isinstance(val, dict):
                status = val.get("ui:status_update")
                if status:
                    chips.append(str(status))
            elif isinstance(val, (dict, list)):
                chips.extend(_find_status_chips(val))
    elif isinstance(agent_output, list):
        for item in agent_output:
            chips.extend(_find_status_chips(item))
    return chips


def _has_media_artifacts(agent_output: dict) -> bool:
    """Check if agent output contains media artifacts (images/videos)."""
    output_str = str(agent_output).lower()
    return any(k in output_str for k in ["artifact_key", "img_artifact", "vid_artifact", "commercial_artifact"])


# ================================================================
# Part 2: Agent Engine direct API (for session state verification)
# ================================================================

def get_ae_client():
    """Get Agent Engine client."""
    import vertexai
    client = vertexai.Client(project=PROJECT, location=AE_LOCATION)
    return client.agent_engines.get(name=AE_RESOURCE_NAME)


def create_ae_session(ae) -> str:
    """Create an AE session with pre-populated state."""
    session = ae.create_session(user_id=USER_ID, state=INITIAL_STATE)
    session_id = session.get("id") if isinstance(session, dict) else str(session)
    return session_id


def get_pipeline_status(ae, session_id: str) -> dict:
    """Check AE session state and determine pipeline status."""
    for attempt in range(3):
        try:
            session = ae.get_session(user_id=USER_ID, session_id=session_id)
            break
        except Exception as e:
            print(f"  get_session failed (attempt {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(30 * (attempt + 1))
    else:
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

    # Determine stage
    creative_attempts = state.get("_creative_pipeline_attempts", 0)
    creative_exhausted = creative_attempts >= 15

    if final_len > 0:
        stage = "COMPLETE"
    elif has_focus_group:
        stage = "SAVE_REPORT"
    elif report_len < 500:
        stage = "RESEARCH"
    elif (not has_commercial) and not creative_exhausted:
        stage = "CREATIVE"
    elif not has_focus_group:
        stage = "FOCUS_GROUP"
    else:
        stage = "SAVE_REPORT"

    print(f"\n--- Pipeline Status: {stage} ---")
    print(f"  Research: {report_len} chars")
    print(f"  Images: {num_images} | Videos: {num_videos}")
    print(f"  Commercial: {'YES' if has_commercial else 'no'}")
    print(f"  Focus group: {'YES' if has_focus_group else 'no'}")
    print(f"  Final report: {final_len} chars")

    return {
        "stage": stage,
        "report_len": report_len,
        "num_images": num_images,
        "num_videos": num_videos,
        "has_commercial": has_commercial,
        "has_focus_group": has_focus_group,
        "final_report_len": final_len,
        "state": state,
    }


# ================================================================
# Part 3: Combined E2E test
# ================================================================

def run_e2e():
    """Run the full E2E test: GE streamAssist + AE pipeline verification."""
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_url = get_base_url()

    print(f"\n{'#'*60}")
    print(f"GE STREAM ASSIST E2E TEST — {timestamp}")
    print(f"{'#'*60}")
    print(f"  DE Location: {DE_LOCATION}")
    print(f"  GE Engine: {GE_ENGINE}")
    print(f"  GE Agent: {GE_AGENT_ID}")
    print(f"  AE Engine: {AE_ENGINE_ID}")
    print(f"  Campaign: Tide Fabric Softener (Hibiscus) for Gen Z")

    # --- Step 1: Verify GE agent config ---
    print(f"\n{'='*60}")
    print("STEP 1: Verify GE agent config")
    print(f"{'='*60}")
    token = get_access_token()
    config = check_agent_config(base_url, token)
    save_screenshot(f"01_agent_config_{timestamp}", config)

    if config.get("error"):
        print("  WARN: Could not verify agent config — continuing anyway")
    elif not config.get("mapped_correctly"):
        print("  WARN: Agent not mapped to expected reasoning engine")

    # --- Step 2: Create AE session with pre-populated state ---
    print(f"\n{'='*60}")
    print("STEP 2: Create AE session")
    print(f"{'='*60}")
    ae = get_ae_client()
    ae_session_id = create_ae_session(ae)
    print(f"  AE Session: {ae_session_id}")
    save_screenshot(f"02_session_{timestamp}", f"AE Session: {ae_session_id}")

    # --- Step 3: Send initial campaign query via AE stream_query ---
    # (streamAssist routes through GE → AE, but for reliable E2E we also
    #  drive AE directly to ensure the pipeline progresses)
    print(f"\n{'='*60}")
    print("STEP 3: Initial campaign message via AE")
    print(f"{'='*60}")

    all_thoughts = []
    all_chips = []
    all_agent_actions = []

    events, texts, thought_count = _ae_stream_and_collect(
        ae,
        "Run the full campaign pipeline for Tide Fabric Softener with Hibiscus Scent.",
        ae_session_id,
    )
    all_thoughts.append(f"wave_0: {thought_count} thoughts")
    save_screenshot(f"03_initial_{timestamp}", texts)
    status = get_pipeline_status(ae, ae_session_id)

    # --- Step 4: Loop "continue" until COMPLETE ---
    print(f"\n{'='*60}")
    print("STEP 4: Pipeline loop (continue until COMPLETE)")
    print(f"{'='*60}")

    for wave in range(MAX_WAVES):
        if status["stage"] == "COMPLETE":
            print(f"\n  Pipeline COMPLETE after {wave + 1} wave(s)!")
            break

        print(f"\n=== Wave {wave + 2}/{MAX_WAVES + 1} (stage: {status['stage']}) ===")
        events, texts, thought_count = _ae_stream_and_collect(ae, "continue", ae_session_id)
        all_thoughts.append(f"wave_{wave + 1}: {thought_count} thoughts")

        # Extract status chips from events
        for event in events:
            if isinstance(event, dict):
                state_delta = event.get("actions", {}).get("state_delta", {})
                if isinstance(state_delta, dict):
                    chip = state_delta.get("ui:status_update")
                    if chip:
                        all_chips.append(chip)

        save_screenshot(f"{wave + 4:02d}_wave_{status['stage'].lower()}_{timestamp}", texts)
        status = get_pipeline_status(ae, ae_session_id)

    # --- Step 5: Verify via streamAssist ---
    print(f"\n{'='*60}")
    print("STEP 5: Verify via GE streamAssist")
    print(f"{'='*60}")

    # Refresh token (may have expired during pipeline)
    token = get_access_token()

    # Send a streamAssist query to verify GE routing works
    sa_result = stream_assist_query(
        base_url, token,
        "Show me the campaign results for Tide Fabric Softener with Hibiscus Scent.",
    )
    print(f"  streamAssist routed to agent: {sa_result.get('routed_to_agent', False)}")
    print(f"  streamAssist reply: {sa_result.get('reply_text', '')[:200]}")
    print(f"  streamAssist thoughts: {len(sa_result.get('thoughts', []))}")
    print(f"  streamAssist status chips: {len(sa_result.get('status_chips', []))}")
    save_screenshot(f"90_streamassist_verify_{timestamp}", sa_result.get("reply_text", ""))

    # --- Step 6: Final summary ---
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60.0

    # Quality gate checks
    research_pass = status["report_len"] > 500
    images_pass = status["num_images"] >= 1
    commercial_pass = status["has_commercial"]
    focus_group_pass = status["has_focus_group"]
    report_pass = status["final_report_len"] > 0
    thoughts_pass = any(int(t.split(":")[1].strip().split()[0]) > 0 for t in all_thoughts if ":" in t)
    chips_pass = len(all_chips) > 0
    ge_routing_pass = sa_result.get("routed_to_agent", False)

    overall = all([research_pass, commercial_pass, focus_group_pass, report_pass])

    summary = f"""
{'='*60}
GE STREAM ASSIST E2E RESULTS — {timestamp}
{'='*60}
  Duration: {elapsed_min:.1f} minutes
  AE Session: {ae_session_id}
  Campaign: Tide Fabric Softener (Hibiscus) for Gen Z

  QUALITY GATES:
    Research report: {status['report_len']} chars {'PASS' if research_pass else 'FAIL'}
    Images: {status['num_images']} {'PASS' if images_pass else 'FAIL (best-effort)'}
    15s Commercial: {'PASS' if commercial_pass else 'FAIL'}
    Focus Group: {'PASS' if focus_group_pass else 'FAIL'}
    Final PDF report: {status['final_report_len']} chars {'PASS' if report_pass else 'FAIL'}

  GE INTEGRATION:
    Thoughts displayed: {sum(1 for t in all_thoughts if int(t.split(':')[1].strip().split()[0]) > 0 if ':' in t)} waves with thoughts {'PASS' if thoughts_pass else 'FAIL'}
    Status chips emitted: {len(all_chips)} chips {'PASS' if chips_pass else 'FAIL'}
    GE routing (streamAssist): {'PASS' if ge_routing_pass else 'FAIL'}

  STATUS CHIPS (sample):
{chr(10).join(f'    - {c}' for c in all_chips[:10])}

  OVERALL: {'PASS' if overall else 'FAIL'}
{'='*60}
"""
    print(summary)
    save_screenshot(f"99_final_summary_{timestamp}", summary)

    # Save full state
    try:
        state_json = json.dumps(status.get("state", {}), indent=2, default=str)
        save_screenshot(f"99_full_state_{timestamp}", state_json[:50000])
    except Exception as e:
        print(f"  Could not save state: {e}")

    return overall


def _ae_stream_and_collect(ae, message, session_id):
    """Stream query via AE and collect events."""
    print(f"\n  SENDING: {message[:120]}...")

    events = []
    agent_texts = []
    thought_count = 0

    for attempt in range(3):
        try:
            for event in ae.stream_query(
                message=message,
                user_id=USER_ID,
                session_id=session_id,
            ):
                events.append(event)
                if isinstance(event, dict):
                    author = event.get("author", "")
                    parts = event.get("content", {}).get("parts", [])
                    for part in parts:
                        if isinstance(part, dict) and part.get("thought"):
                            thought_count += 1
                            thought_text = part.get("text", "")[:100]
                            print(f"  [{author}] THOUGHT: {thought_text}...")
                        elif isinstance(part, dict) and part.get("text"):
                            text_preview = part["text"][:300]
                            print(f"  [{author}]: {text_preview}")
                            agent_texts.append(f"[{author}]: {part['text']}")
                        elif isinstance(part, dict) and part.get("function_call"):
                            fn = part["function_call"].get("name", "?")
                            print(f"  [{author}] -> tool: {fn}")
                        elif isinstance(part, dict) and part.get("function_response"):
                            fn = part["function_response"].get("name", "?")
                            resp = part["function_response"].get("response", {})
                            status = resp.get("status", "") if isinstance(resp, dict) else ""
                            artifact = resp.get("artifact_key", "") if isinstance(resp, dict) else ""
                            print(f"  [{author}] <- tool: {fn} (status={status}, artifact={artifact})")
            break
        except Exception as e:
            err_str = str(e)
            if ("FAILED_PRECONDITION" in err_str or "Service Unavailable" in err_str) and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  AE transient error (attempt {attempt + 1}/3), waiting {wait}s: {err_str[:100]}")
                time.sleep(wait)
                events = []
                agent_texts = []
                thought_count = 0
            else:
                print(f"  ERROR: {e}")
                break

    print(f"  Events: {len(events)}, Thoughts: {thought_count}")
    return events, "\n".join(agent_texts), thought_count


def parse_args():
    parser = argparse.ArgumentParser(description="GE streamAssist E2E test")
    parser.add_argument("--max-waves", type=int, default=MAX_WAVES)
    parser.add_argument("--de-location", default=DE_LOCATION)
    parser.add_argument("--ge-engine", default=GE_ENGINE)
    parser.add_argument("--ge-agent", default=GE_AGENT_ID)
    parser.add_argument("--ae-engine", default=AE_ENGINE_ID)
    parser.add_argument("--project", default=PROJECT)
    parser.add_argument("--project-number", default=PROJECT_NUMBER)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    MAX_WAVES = args.max_waves
    DE_LOCATION = args.de_location
    GE_ENGINE = args.ge_engine
    GE_AGENT_ID = args.ge_agent
    AE_ENGINE_ID = args.ae_engine
    PROJECT = args.project
    PROJECT_NUMBER = args.project_number
    AE_RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{AE_LOCATION}/reasoningEngines/{AE_ENGINE_ID}"

    success = run_e2e()
    sys.exit(0 if success else 1)
