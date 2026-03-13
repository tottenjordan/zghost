"""
E2E test for Agent Engine deployment.
Drives the full pipeline: trends -> research -> ad creatives -> final report.
"""
import os
import json
import time
from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

import vertexai

PROJECT = "wortz-project-352116"
LOCATION = "us-central1"
ENGINE_ID = "751062099282624512"
RESOURCE_NAME = f"projects/679926387543/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"
USER_ID = "e2e_test_user"

# Pre-populated state to skip trend selection
INITIAL_STATE = {
    "brand": "Nike",
    "target_product": "Air Max Pulse",
    "target_audience": "Gen Z sneaker enthusiasts and streetwear culture fans",
    "key_selling_points": "Inspired by the icons that Icons that Icons that came before. The Air Max Pulse pulls design cues from the Air Max archives.",
    "target_search_trends": {"target_search_trends": [
        {"title": "Sneaker Culture", "description": "Rising interest in sneaker collecting and streetwear fashion"}
    ]},
    "target_yt_trends": {"target_yt_trends": [
        {"title": "Best Sneakers 2026", "description": "YouTube creators reviewing the top sneaker releases"}
    ]},
    "yt_video_analysis": "YouTube trend analysis: Gen Z audiences are drawn to sneakers that blend retro aesthetics with modern comfort tech. Key themes: nostalgia, self-expression, sustainability.",
    # Initialize empty artifact lists
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


def stream_and_collect(ae, message, session_id):
    """Send a message via stream_query and collect all events."""
    print(f"\n{'='*60}")
    print(f"SENDING: {message[:100]}...")
    print(f"{'='*60}")

    events = []
    try:
        for event in ae.stream_query(
            message=message,
            user_id=USER_ID,
            session_id=session_id,
        ):
            events.append(event)
            # Print agent text responses
            if isinstance(event, dict):
                author = event.get("author", "")
                parts = event.get("content", {}).get("parts", [])
                for part in parts:
                    if isinstance(part, dict) and part.get("text"):
                        text_preview = part["text"][:200]
                        print(f"  [{author}]: {text_preview}")
                    elif isinstance(part, dict) and part.get("function_call"):
                        fn = part["function_call"].get("name", "?")
                        print(f"  [{author}] -> tool: {fn}")
                    elif isinstance(part, dict) and part.get("function_response"):
                        fn = part["function_response"].get("name", "?")
                        print(f"  [{author}] <- tool response: {fn}")
    except Exception as e:
        print(f"  ERROR during stream: {e}")

    print(f"  Total events: {len(events)}")
    return events


def check_session_state(ae, session_id):
    """Get session and check key state fields."""
    session = ae.get_session(user_id=USER_ID, session_id=session_id)
    state = session.get("state", {}) if isinstance(session, dict) else {}

    report = state.get("combined_final_cited_report", "")
    imgs = state.get("img_artifact_keys", {})
    vids = state.get("vid_artifact_keys", {})
    final = state.get("final_report_with_citations", "")

    # Normalize artifact lists
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
    }


def run_e2e():
    print(f"Initializing vertexai: project={PROJECT}, location={LOCATION}")
    client = vertexai.Client(project=PROJECT, location=LOCATION)

    print(f"Loading Agent Engine: {RESOURCE_NAME}")
    ae = client.agent_engines.get(name=RESOURCE_NAME)

    # Step 1: Create session with pre-populated state
    print("\n=== STEP 1: Create Session ===")
    session = ae.create_session(user_id=USER_ID, state=INITIAL_STATE)
    session_id = session.get("id") if isinstance(session, dict) else str(session)
    print(f"Session created: {session_id}")

    # Step 2: Kick off research (trends already in state)
    print("\n=== STEP 2: Start Research ===")
    research_msg = (
        "Campaign metadata is already loaded in state. Trends have been selected. "
        "Skip the trends_and_insights_agent step - trends are already captured. "
        "Transfer directly to the research_orchestrator to begin market research now. "
        "Do not ask for confirmation, just start the research."
    )
    events = stream_and_collect(ae, research_msg, session_id)

    # Check state after research
    status = check_session_state(ae, session_id)

    if status["report_len"] == 0:
        print("\nResearch report empty. Sending follow-up...")
        followup = "Please continue with the research. The research_orchestrator should complete all steps and produce the combined_final_cited_report."
        events = stream_and_collect(ae, followup, session_id)
        status = check_session_state(ae, session_id)

    # Step 3: Ad creative generation
    print("\n=== STEP 3: Ad Creative Generation ===")
    creative_msg = (
        "The research report looks great. Now transfer to the ad_content_generator_agent "
        "to generate ad creatives. Create compelling visual concepts and generate images and videos. "
        "Proceed without asking for confirmation."
    )
    events = stream_and_collect(ae, creative_msg, session_id)
    status = check_session_state(ae, session_id)

    if status["num_images"] == 0 and status["num_videos"] == 0:
        print("\nNo creatives yet. Sending follow-up...")
        followup = "Please continue generating ad creatives - create images and video concepts using the visual generation tools."
        events = stream_and_collect(ae, followup, session_id)
        status = check_session_state(ae, session_id)

    # Step 4: Final report
    print("\n=== STEP 4: Final Report ===")
    report_msg = (
        "All creatives look great. Now use the save_creatives_and_research_report tool "
        "to build the final report detailing the research and creatives generated."
    )
    events = stream_and_collect(ae, report_msg, session_id)
    status = check_session_state(ae, session_id)

    # Final summary
    print("\n" + "=" * 60)
    print("E2E TEST RESULTS")
    print("=" * 60)
    print(f"  Session ID: {session_id}")
    print(f"  Research report: {status['report_len']} chars {'PASS' if status['report_len'] > 0 else 'FAIL'}")
    print(f"  Images: {status['num_images']} {'PASS' if status['num_images'] > 0 else 'FAIL'}")
    print(f"  Videos: {status['num_videos']} {'PASS' if status['num_videos'] > 0 else 'FAIL'}")
    print(f"  Final report: {status['final_report_len']} chars {'PASS' if status['final_report_len'] > 0 else 'FAIL'}")

    all_pass = (
        status["report_len"] > 0
        and status["num_images"] > 0
        and status["num_videos"] > 0
        and status["final_report_len"] > 0
    )
    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return all_pass


if __name__ == "__main__":
    run_e2e()
