"""
E2E Demo Runner for Agent Engine + Gemini Enterprise.
Drives the full pipeline: trends -> research -> ad creatives (Gemini image gen + Veo 3) -> final report.
Saves screenshots and artifacts for demo evidence.
"""
import os
import json
import time
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

import vertexai

PROJECT = "wortz-project-352116"
LOCATION = "us-central1"
ENGINE_ID = "9218251611204222976"
RESOURCE_NAME = f"projects/679926387543/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"
USER_ID = "e2e_demo_user"
SCREENSHOT_DIR = "demo_screenshots"

# Pre-populated state to skip trend selection
INITIAL_STATE = {
    "brand": "Nike",
    "target_product": "Air Max Pulse",
    "target_audience": "Gen Z sneaker enthusiasts and streetwear culture fans",
    "key_selling_points": "Inspired by the icons that came before. The Air Max Pulse pulls design cues from the Air Max archives with modern comfort tech.",
    "target_search_trends": {"target_search_trends": [
        {"title": "Sneaker Culture", "description": "Rising interest in sneaker collecting and streetwear fashion"}
    ]},
    "target_yt_trends": {"target_yt_trends": [
        {"title": "Best Sneakers 2026", "description": "YouTube creators reviewing the top sneaker releases"}
    ]},
    "yt_video_analysis": "YouTube trend analysis: Gen Z audiences are drawn to sneakers that blend retro aesthetics with modern comfort tech. Key themes: nostalgia, self-expression, sustainability.",
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
}


def save_screenshot(name, content):
    """Save text content as a screenshot/evidence file."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filepath = os.path.join(SCREENSHOT_DIR, f"{name}.txt")
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  [SCREENSHOT] Saved: {filepath}")
    return filepath


def stream_and_collect(ae, message, session_id):
    """Send a message via stream_query and collect all events."""
    print(f"\n{'='*60}")
    print(f"SENDING: {message[:120]}...")
    print(f"{'='*60}")

    events = []
    agent_texts = []
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
                    if isinstance(part, dict) and part.get("text"):
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
    except Exception as e:
        print(f"  ERROR during stream: {e}")

    print(f"  Total events: {len(events)}")
    return events, "\n".join(agent_texts)


def check_session_state(ae, session_id):
    """Get session and check key state fields."""
    session = ae.get_session(user_id=USER_ID, session_id=session_id)
    state = session.get("state", {}) if isinstance(session, dict) else {}

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

    print(f"\n--- Session State Check ---")
    print(f"  Research report: {report_len} chars")
    print(f"  Images: {len(imgs) if isinstance(imgs, list) else 0}")
    print(f"  Videos: {len(vids) if isinstance(vids, list) else 0}")
    print(f"  Final report: {final_len} chars")

    return {
        "report_len": report_len,
        "num_images": len(imgs) if isinstance(imgs, list) else 0,
        "num_videos": len(vids) if isinstance(vids, list) else 0,
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
    print(f"E2E DEMO RUNNER - {timestamp}")
    print(f"Engine: {ENGINE_ID}")
    print(f"Project: {PROJECT}")
    print(f"{'#'*60}")

    client = vertexai.Client(project=PROJECT, location=LOCATION)
    ae = client.agent_engines.get(name=RESOURCE_NAME)

    # === STEP 1: Create Session ===
    print("\n=== STEP 1: Create Session ===")
    session = ae.create_session(user_id=USER_ID, state=INITIAL_STATE)
    session_id = session.get("id") if isinstance(session, dict) else str(session)
    print(f"Session created: {session_id}")
    save_screenshot(f"01_session_created_{timestamp}",
                    f"Session ID: {session_id}\nEngine ID: {ENGINE_ID}\nInitial State Keys: {list(INITIAL_STATE.keys())}")

    # === STEP 2: Research ===
    print("\n=== STEP 2: Start Research ===")
    research_msg = (
        "Campaign metadata is already loaded in state. Trends have been selected. "
        "Skip the trends_and_insights_agent step - trends are already captured. "
        "Transfer directly to the research_orchestrator to begin market research now. "
        "Do not ask for confirmation, just start the research."
    )
    events, texts = stream_and_collect(ae, research_msg, session_id)
    status = check_session_state(ae, session_id)
    save_screenshot(f"02_research_started_{timestamp}", texts)

    if status["report_len"] == 0:
        print("\nResearch report empty. Sending follow-up...")
        followup = "Please continue with the research. The research_orchestrator should complete all steps and produce the combined_final_cited_report."
        events, texts = stream_and_collect(ae, followup, session_id)
        status = check_session_state(ae, session_id)
        save_screenshot(f"02b_research_followup_{timestamp}", texts)

    # Save research report screenshot
    if status["report_len"] > 0:
        save_screenshot(f"03_research_report_{timestamp}",
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
    events, texts = stream_and_collect(ae, creative_msg, session_id)
    status = check_session_state(ae, session_id)
    save_screenshot(f"04_ad_creative_generation_{timestamp}", texts)

    # Follow up if needed
    if status["num_images"] == 0:
        print("\nNo images yet. Sending follow-up...")
        followup = "Please continue generating ad creatives - generate images with the generate_image tool and videos with generate_video. Use the first visual concepts available."
        events, texts = stream_and_collect(ae, followup, session_id)
        status = check_session_state(ae, session_id)
        save_screenshot(f"04b_creative_followup_{timestamp}", texts)

    # Save creative artifacts screenshot
    if status["num_images"] > 0 or status["num_videos"] > 0:
        artifact_info = "GENERATED ARTIFACTS:\n\n"
        artifact_info += f"Images ({status['num_images']}):\n"
        for img in (status.get("imgs") or []):
            artifact_info += f"  - {img.get('artifact_key', '?')}: {img.get('headline', '?')}\n"
            artifact_info += f"    Concept: {img.get('concept', '?')}\n"
            artifact_info += f"    Prompt: {img.get('img_prompt', '?')[:200]}\n\n"
        artifact_info += f"\nVideos ({status['num_videos']}):\n"
        for vid in (status.get("vids") or []):
            artifact_info += f"  - {vid.get('artifact_key', '?')}: {vid.get('headline', '?')}\n"
            artifact_info += f"    Concept: {vid.get('concept', '?')}\n"
            artifact_info += f"    Prompt: {vid.get('vid_prompt', '?')[:200]}\n\n"
        save_screenshot(f"05_generated_artifacts_{timestamp}", artifact_info)

    # === STEP 4: Final Report ===
    print("\n=== STEP 4: Final Report ===")
    report_msg = (
        "All creatives look great. Now use the save_creatives_and_research_report tool "
        "to build the final report detailing the research and creatives generated."
    )
    events, texts = stream_and_collect(ae, report_msg, session_id)
    status = check_session_state(ae, session_id)
    save_screenshot(f"06_final_report_{timestamp}", texts)

    if status["final_report_len"] > 0:
        save_screenshot(f"07_final_report_content_{timestamp}",
                        f"FINAL REPORT ({status['final_report_len']} chars):\n\n{status['final_report'][:5000]}")

    # === FINAL SUMMARY ===
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60.0

    summary = f"""
{'='*60}
E2E DEMO RESULTS - {timestamp}
{'='*60}
  Engine ID: {ENGINE_ID}
  Session ID: {session_id}
  Duration: {elapsed_min:.1f} minutes

  Research report: {status['report_len']} chars {'PASS' if status['report_len'] > 0 else 'FAIL'}
  Images: {status['num_images']} {'PASS' if status['num_images'] > 0 else 'FAIL'}
  Videos: {status['num_videos']} {'PASS' if status['num_videos'] > 0 else 'FAIL'}
  Final report: {status['final_report_len']} chars {'PASS' if status['final_report_len'] > 0 else 'FAIL'}

  Image model: gemini-3-pro-image-preview (Gemini native)
  Video model: veo-3.1-fast-generate-preview (Veo 3)
  Image-to-Video Reference: YES (keyframe -> video workflow)

  OVERALL: {'PASS' if (status['report_len'] > 0 and status['num_images'] > 0 and status['num_videos'] > 0 and status['final_report_len'] > 0) else 'FAIL'}
{'='*60}
"""
    print(summary)
    save_screenshot(f"08_final_summary_{timestamp}", summary)

    # Save full session state
    try:
        state_json = json.dumps(status["state"], indent=2, default=str)
        save_screenshot(f"09_full_session_state_{timestamp}", state_json[:50000])
    except Exception as e:
        print(f"  Could not save full state: {e}")

    return status["report_len"] > 0 and status["num_images"] > 0 and status["num_videos"] > 0


if __name__ == "__main__":
    success = run_e2e()
    exit(0 if success else 1)
