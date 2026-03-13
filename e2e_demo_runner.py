"""
E2E Demo Runner for Agent Engine + CampaignOrchestrator.

The CampaignOrchestrator is a deterministic BaseAgent that checks session state
keys to decide which stage to run next. On AE, stream_query returns after each
"wave" of events. This runner simply re-invokes with "continue" and the
orchestrator automatically resumes from the correct stage.
"""
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

import vertexai

PROJECT = "wortz-project-352116"
LOCATION = "us-central1"
ENGINE_ID = "8788263399906607104"
RESOURCE_NAME = f"projects/679926387543/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"
USER_ID = "e2e_demo_user"
SCREENSHOT_DIR = "demo_screenshots"

# Max re-invocations before giving up
MAX_WAVES = 35

# Pre-populated state to skip trend selection - Tide Fabric Softener campaign
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


def save_screenshot(name, content):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filepath = os.path.join(SCREENSHOT_DIR, f"{name}.txt")
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  [SCREENSHOT] Saved: {filepath}")
    return filepath


def stream_and_collect(ae, message, session_id):
    print(f"\n{'='*60}")
    print(f"SENDING: {message[:120]}...")
    print(f"{'='*60}")

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
                            print(f"  [{author}] <- tool response: {fn} (status={status}, artifact={artifact})")
            break  # Success
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
                print(f"  ERROR during stream: {e}")
                break

    print(f"  Total events: {len(events)}, Thoughts: {thought_count}")
    return events, "\n".join(agent_texts), thought_count


def get_pipeline_status(ae, session_id):
    """Check session state and determine current pipeline status."""
    # Retry get_session — AE instances can restart between waves
    session = None
    for attempt in range(3):
        try:
            session = ae.get_session(user_id=USER_ID, session_id=session_id)
            break
        except Exception as e:
            print(f"  get_session failed (attempt {attempt + 1}/3): {e}")
            if attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  Waiting {wait}s before retry...")
                time.sleep(wait)
    if session is None:
        print("  ERROR: Could not retrieve session after 3 attempts")
        return {"stage": "UNKNOWN", "report_len": 0, "num_images": 0,
                "num_videos": 0, "has_commercial": False, "has_focus_group": False,
                "final_report_len": 0, "state": {}, "report": "", "final_report": "",
                "commercial": "", "focus_group": "", "imgs": [], "vids": []}
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

    # Determine stage — check COMPLETE first (creative exhaustion can skip stages)
    if final_len > 0:
        stage = "COMPLETE"
    elif has_focus_group:
        stage = "SAVE_REPORT"
    elif report_len < 500:
        stage = "RESEARCH"
    elif num_images < 2 or not has_commercial:
        stage = "CREATIVE"
    else:
        stage = "FOCUS_GROUP"

    print(f"\n--- Pipeline Status: {stage} ---")
    print(f"  Research report: {report_len} chars")
    print(f"  Images: {num_images}")
    print(f"  Videos: {num_videos}")
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
        "report": report,
        "final_report": final,
        "commercial": commercial,
        "focus_group": focus_group,
        "imgs": imgs,
        "vids": vids,
    }


def run_e2e():
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n{'#'*60}")
    print(f"E2E DEMO RUNNER (CampaignOrchestrator) - {timestamp}")
    print(f"Engine: {ENGINE_ID}")
    print(f"Project: {PROJECT}")
    print(f"{'#'*60}")

    client = vertexai.Client(project=PROJECT, location=LOCATION)
    ae = client.agent_engines.get(name=RESOURCE_NAME)

    # Create session with pre-populated state (trends already selected)
    print("\n=== Creating Session ===")
    session = ae.create_session(user_id=USER_ID, state=INITIAL_STATE)
    session_id = session.get("id") if isinstance(session, dict) else str(session)
    print(f"Session created: {session_id}")
    save_screenshot(f"01_session_created_{timestamp}",
                    f"Session ID: {session_id}\nEngine ID: {ENGINE_ID}\nInitial State Keys: {list(INITIAL_STATE.keys())}")

    # Initial kickoff — orchestrator determines stage from state
    events, texts, thoughts = stream_and_collect(
        ae,
        "Run the full campaign pipeline for Tide Fabric Softener with Hibiscus Scent.",
        session_id,
    )
    save_screenshot(f"02_initial_{timestamp}", texts)
    status = get_pipeline_status(ae, session_id)

    # Loop: re-invoke until COMPLETE or max waves reached
    for wave in range(MAX_WAVES):
        if status["stage"] == "COMPLETE":
            print(f"\n  Pipeline COMPLETE after {wave + 1} wave(s)!")
            break

        print(f"\n=== Wave {wave + 2}/{MAX_WAVES + 1} (stage: {status['stage']}) ===")
        events, texts, thoughts = stream_and_collect(ae, "continue", session_id)
        save_screenshot(f"{wave + 3:02d}_wave_{status['stage'].lower()}_{timestamp}", texts)
        status = get_pipeline_status(ae, session_id)

    # Final summary
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60.0

    summary = f"""
{'='*60}
E2E DEMO RESULTS (CampaignOrchestrator) - {timestamp}
{'='*60}
  Engine ID: {ENGINE_ID}
  Session ID: {session_id}
  Duration: {elapsed_min:.1f} minutes
  Campaign: Tide Fabric Softener (Hibiscus) for Gen Z

  Research report: {status['report_len']} chars {'PASS' if status['report_len'] > 500 else 'FAIL'}
  Images: {status['num_images']} {'PASS' if status['num_images'] >= 2 else 'FAIL'}
  Videos: {status['num_videos']} {'PASS' if status['num_videos'] >= 2 else 'FAIL'}
  15s Commercial: {'PASS' if status['has_commercial'] else 'FAIL'}
  Focus Group: {'PASS' if status['has_focus_group'] else 'FAIL'}
  Final report: {status['final_report_len']} chars {'PASS' if status['final_report_len'] > 0 else 'FAIL'}

  OVERALL: {'PASS' if (status['report_len'] > 500 and status['num_images'] >= 2 and status['num_videos'] >= 2 and status['has_commercial'] and status['has_focus_group'] and status['final_report_len'] > 0) else 'FAIL'}
{'='*60}
"""
    print(summary)
    save_screenshot(f"99_final_summary_{timestamp}", summary)

    # Save full session state
    try:
        state_json = json.dumps(status["state"], indent=2, default=str)
        save_screenshot(f"99_full_session_state_{timestamp}", state_json[:50000])
    except Exception as e:
        print(f"  Could not save full state: {e}")

    return (status["report_len"] > 500 and status["num_images"] >= 2
            and status["num_videos"] >= 2 and status["has_commercial"]
            and status["has_focus_group"] and status["final_report_len"] > 0)


if __name__ == "__main__":
    success = run_e2e()
    exit(0 if success else 1)
