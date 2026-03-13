"""
Local E2E Runner for ADK Web Server - Tide Fabric Softener Campaign.
Tests the full pipeline against adk web on localhost:8000.
"""
import json
import time
import uuid
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
APP_NAME = "trends_and_insights_agent"
USER_ID = f"ralph_e2e_{uuid.uuid4().hex[:8]}"
SCREENSHOT_DIR = "ralph_screenshots"

INITIAL_STATE = {
    "_state_init": True,  # Skip _load_session_state callback overwrite
    "brand": "Tide",
    "target_product": "Tide Fabric Softener with Hibiscus Scent",
    "target_audience": "Gen Z eco-conscious consumers who value sustainable products and fresh scents",
    "key_selling_points": "New Hibiscus Scent. Plant-based formula. 2x cleaning power. Biodegradable packaging.",
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
    "commercial_duration": 30,
    "commercial_artifact": "",
    "campaign_guide_content": "",
    "gcs_folder": "",
}


def save_evidence(name, content):
    """Save text content as evidence file."""
    import os
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filepath = os.path.join(SCREENSHOT_DIR, f"{name}.txt")
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  [SAVED] {filepath}")
    return filepath


def create_session():
    """Create a session with pre-populated state via ADK web API."""
    url = f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions"
    resp = requests.post(url, json={"state": INITIAL_STATE}, timeout=30)
    resp.raise_for_status()
    session = resp.json()
    session_id = session.get("id", "")
    print(f"  Session created: {session_id}")
    return session_id


def get_session_state(session_id):
    """Get session state via ADK web API."""
    url = f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    session = resp.json()
    return session.get("state", {})


def send_message_sse(session_id, message):
    """Send a message via /run_sse and stream events. Returns collected event texts."""
    url = f"{BASE_URL}/run_sse"
    print(f"\n{'='*60}")
    print(f"SENDING: {message[:120]}...")
    print(f"{'='*60}")

    agent_texts = []
    event_count = 0

    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": message}],
        },
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            stream=True,
            timeout=1800,  # 30 min timeout for long pipelines
        )
        resp.raise_for_status()

        buffer = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if not data_str or data_str == "[DONE]":
                            continue
                        try:
                            event = json.loads(data_str)
                            event_count += 1
                            _print_event(event, agent_texts)
                        except json.JSONDecodeError:
                            pass
    except requests.exceptions.Timeout:
        print("  TIMEOUT after 30 minutes")
    except Exception as e:
        print(f"  ERROR during stream: {e}")

    print(f"  Total events: {event_count}")
    return "\n".join(agent_texts)


def _print_event(event, agent_texts):
    """Print a parsed SSE event."""
    author = event.get("author", "")
    content = event.get("content", {})
    parts = content.get("parts", []) if isinstance(content, dict) else []

    # Skip thought-only events (no visible text)
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text", "")
        is_thought = part.get("thought", False)
        if text and not is_thought:
            text_preview = text[:300]
            print(f"  [{author}]: {text_preview}")
            agent_texts.append(f"[{author}]: {text}")
        elif part.get("functionCall"):
            fc = part["functionCall"]
            fn = fc.get("name", "?")
            print(f"  [{author}] -> tool: {fn}")
        elif part.get("functionResponse"):
            fr = part["functionResponse"]
            fn = fr.get("name", "?")
            resp_data = fr.get("response", {})
            status = resp_data.get("status", "") if isinstance(resp_data, dict) else ""
            artifact = resp_data.get("artifact_key", "") if isinstance(resp_data, dict) else ""
            print(f"  [{author}] <- tool response: {fn} (status={status}, artifact={artifact})")

    # Print status updates from state delta
    actions = event.get("actions", {})
    state_delta = actions.get("stateDelta", {})
    status_msg = state_delta.get("ui:status_update")
    if status_msg:
        print(f"  [STATUS] {status_msg}")


def check_state(session_id):
    """Check key session state fields and print summary."""
    state = get_session_state(session_id)

    report = state.get("combined_final_cited_report", "")
    imgs = state.get("img_artifact_keys", {})
    vids = state.get("vid_artifact_keys", {})
    final = state.get("final_report_with_citations", "")

    if isinstance(imgs, dict):
        imgs = imgs.get("img_artifact_keys", [])
    if isinstance(vids, dict):
        vids = vids.get("vid_artifact_keys", [])

    report_len = len(report) if isinstance(report, str) else 0
    final_len = len(final) if isinstance(final, str) else 0
    num_images = len(imgs) if isinstance(imgs, list) else 0
    num_videos = len(vids) if isinstance(vids, list) else 0

    print(f"\n--- Session State Check ---")
    print(f"  Research report: {report_len} chars")
    print(f"  Images: {num_images}")
    print(f"  Videos: {num_videos}")
    print(f"  Final report: {final_len} chars")

    return {
        "report_len": report_len,
        "num_images": num_images,
        "num_videos": num_videos,
        "final_report_len": final_len,
        "state": state,
        "imgs": imgs,
        "vids": vids,
        "report": report,
        "final_report": final,
    }


def run_e2e():
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n{'#'*60}")
    print(f"RALPH E2E RUNNER (local adk web) - {timestamp}")
    print(f"Brand: Tide | Product: Fabric Softener with Hibiscus Scent")
    print(f"Server: {BASE_URL}")
    print(f"User: {USER_ID}")
    print(f"{'#'*60}")

    # === STEP 1: Create Session ===
    print("\n=== STEP 1: Create Session ===")
    session_id = create_session()
    save_evidence(f"01_session_{timestamp}",
                  f"Session ID: {session_id}\nUser ID: {USER_ID}\nState Keys: {list(INITIAL_STATE.keys())}")

    # === STEP 2: Research ===
    print("\n=== STEP 2: Start Research ===")
    research_msg = (
        "Campaign metadata is already loaded in state. Trends have been selected. "
        "Skip the trends_and_insights_agent step - trends are already captured. "
        "Transfer directly to the research_orchestrator to begin market research now. "
        "Do not ask for confirmation, just start the research."
    )
    texts = send_message_sse(session_id, research_msg)
    status = check_state(session_id)
    save_evidence(f"02_research_{timestamp}", texts)

    if status["report_len"] == 0:
        print("\nResearch report empty. Sending follow-up...")
        followup = (
            "Please continue with the research. The research_orchestrator should complete "
            "all steps and produce the combined_final_cited_report."
        )
        texts = send_message_sse(session_id, followup)
        status = check_state(session_id)
        save_evidence(f"02b_research_followup_{timestamp}", texts)

    if status["report_len"] > 0:
        save_evidence(f"03_research_report_{timestamp}",
                      f"RESEARCH REPORT ({status['report_len']} chars):\n\n{status['report'][:5000]}")

    # === STEP 3: Ad Creative Generation ===
    print("\n=== STEP 3: Ad Creative Generation ===")
    creative_msg = (
        "The research report is complete. Now transfer to the ad_content_generator_agent "
        "to generate ad creatives. Create compelling visual concepts and generate images using "
        "Gemini native image generation and videos using Veo 3. "
        "For each visual concept, generate the keyframe image first, then use it as a reference "
        "for video generation. Proceed without asking for confirmation - select the first/best options automatically."
    )
    texts = send_message_sse(session_id, creative_msg)
    status = check_state(session_id)
    save_evidence(f"04_ad_creative_{timestamp}", texts)

    if status["num_images"] == 0:
        print("\nNo images yet. Sending follow-up...")
        followup = (
            "Please continue generating ad creatives - generate images with the generate_image "
            "tool and videos with generate_video. Use the first visual concepts available."
        )
        texts = send_message_sse(session_id, followup)
        status = check_state(session_id)
        save_evidence(f"04b_creative_followup_{timestamp}", texts)

    if status["num_images"] > 0 or status["num_videos"] > 0:
        artifact_info = "GENERATED ARTIFACTS:\n\n"
        artifact_info += f"Images ({status['num_images']}):\n"
        for img in (status.get("imgs") or []):
            if isinstance(img, dict):
                artifact_info += f"  - {img.get('artifact_key', '?')}: {img.get('headline', '?')}\n"
                artifact_info += f"    Concept: {img.get('concept', '?')}\n"
                artifact_info += f"    Prompt: {str(img.get('img_prompt', '?'))[:200]}\n\n"
        artifact_info += f"\nVideos ({status['num_videos']}):\n"
        for vid in (status.get("vids") or []):
            if isinstance(vid, dict):
                artifact_info += f"  - {vid.get('artifact_key', '?')}: {vid.get('headline', '?')}\n"
                artifact_info += f"    Concept: {vid.get('concept', '?')}\n"
                artifact_info += f"    Prompt: {str(vid.get('vid_prompt', '?'))[:200]}\n\n"
        save_evidence(f"05_artifacts_{timestamp}", artifact_info)

    # === STEP 4: Final Report ===
    print("\n=== STEP 4: Final Report ===")
    report_msg = (
        "All creatives look great. Now use the save_creatives_and_research_report tool "
        "to build the final report detailing the research and creatives generated."
    )
    texts = send_message_sse(session_id, report_msg)
    status = check_state(session_id)
    save_evidence(f"06_final_report_{timestamp}", texts)

    if status["final_report_len"] > 0:
        save_evidence(f"07_final_report_content_{timestamp}",
                      f"FINAL REPORT ({status['final_report_len']} chars):\n\n{status['final_report'][:5000]}")

    # === FINAL SUMMARY ===
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60.0

    summary = f"""
{'='*60}
RALPH E2E RESULTS - {timestamp}
{'='*60}
  Brand: Tide
  Product: Tide Fabric Softener with Hibiscus Scent
  Server: {BASE_URL}
  Session ID: {session_id}
  Duration: {elapsed_min:.1f} minutes

  Research report: {status['report_len']} chars {'PASS' if status['report_len'] > 0 else 'FAIL'}
  Images: {status['num_images']} {'PASS' if status['num_images'] > 0 else 'FAIL'}
  Videos: {status['num_videos']} {'PASS' if status['num_videos'] > 0 else 'FAIL'}
  Final report: {status['final_report_len']} chars {'PASS' if status['final_report_len'] > 0 else 'FAIL'}

  OVERALL: {'PASS' if (status['report_len'] > 0 and status['num_images'] > 0 and status['num_videos'] > 0) else 'FAIL'}
{'='*60}
"""
    print(summary)
    save_evidence(f"08_summary_{timestamp}", summary)

    try:
        state_json = json.dumps(status["state"], indent=2, default=str)
        save_evidence(f"09_full_state_{timestamp}", state_json[:50000])
    except Exception as e:
        print(f"  Could not save full state: {e}")

    return status["report_len"] > 0 and status["num_images"] > 0 and status["num_videos"] > 0


if __name__ == "__main__":
    success = run_e2e()
    exit(0 if success else 1)
