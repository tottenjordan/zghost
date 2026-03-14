"""Test GE interactive flow — simulates a user starting from scratch in Gemini Enterprise.

Unlike e2e_demo_runner.py which pre-populates trends, this tests the TRENDS stage
that was previously stuck due to "transfer to root_agent" text loop.
"""
import os
import time
from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

import vertexai

# Defaults — override via env vars
PROJECT = os.environ.get("GCP_PROJECT", "wortz-project-352116")
PROJECT_NUMBER = os.environ.get("GCP_PROJECT_NUMBER", "679926387543")
LOCATION = os.environ.get("AE_LOCATION", "us-central1")
ENGINE_ID = os.environ.get("AE_ENGINE_ID", "8788263399906607104")
RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"
USER_ID = "ge_interactive_test"

# Minimal initial state — NO pre-populated trends
INITIAL_STATE = {
    "brand": "Tide",
    "target_product": "Tide Fabric Softener with Hibiscus Scent",
    "target_audience": "Gen Z eco-conscious consumers who value sustainable products and fresh scents",
    "key_selling_points": "New Hibiscus Scent. Plant-based formula. 2x cleaning power. Biodegradable packaging.",
    "autopilot_mode": True,
    "commercial_duration": 15,
    # These are EMPTY — trends agent must populate them
    "target_search_trends": {"target_search_trends": []},
    "target_yt_trends": {"target_yt_trends": []},
    "final_select_ad_copies": {"final_select_ad_copies": []},
    "final_select_vis_concepts": {"final_select_vis_concepts": []},
    "img_artifact_keys": {"img_artifact_keys": []},
    "vid_artifact_keys": {"vid_artifact_keys": []},
    "combined_web_search_insights": "",
    "combined_final_cited_report": "",
    "final_report_with_citations": "",
    "commercial_artifact": "",
    "gcs_folder": "",
}


def stream_and_print(ae, message, session_id):
    print(f"\n{'='*60}")
    print(f"USER: {message}")
    print(f"{'='*60}")

    for attempt in range(3):
        try:
            for event in ae.stream_query(
                message=message,
                user_id=USER_ID,
                session_id=session_id,
            ):
                if isinstance(event, dict):
                    author = event.get("author", "")
                    parts = event.get("content", {}).get("parts", [])
                    for part in parts:
                        if isinstance(part, dict) and part.get("thought"):
                            print(f"  [{author}] THOUGHT: {part.get('text', '')[:120]}...")
                        elif isinstance(part, dict) and part.get("text"):
                            print(f"  [{author}]: {part['text'][:400]}")
                        elif isinstance(part, dict) and part.get("function_call"):
                            fn = part["function_call"].get("name", "?")
                            print(f"  [{author}] -> tool: {fn}")
                        elif isinstance(part, dict) and part.get("function_response"):
                            fn = part["function_response"].get("name", "?")
                            resp = part["function_response"].get("response", {})
                            status = resp.get("status", "") if isinstance(resp, dict) else ""
                            print(f"  [{author}] <- tool: {fn} (status={status})")
            break
        except Exception as e:
            err = str(e)
            if ("FAILED_PRECONDITION" in err or "Service Unavailable" in err) and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  Transient error, waiting {wait}s: {err[:100]}")
                time.sleep(wait)
            else:
                print(f"  ERROR: {e}")
                break


def check_state(ae, session_id):
    for attempt in range(3):
        try:
            session = ae.get_session(user_id=USER_ID, session_id=session_id)
            break
        except Exception as e:
            if attempt < 2:
                print(f"  get_session error (attempt {attempt+1}/3), waiting {30*(attempt+1)}s: {str(e)[:80]}")
                time.sleep(30 * (attempt + 1))
            else:
                print(f"  get_session failed after 3 attempts: {e}")
                return {"has_search_trends": False, "has_yt_trends": False, "report_len": 0}
    state = session.get("state", {}) if isinstance(session, dict) else {}

    search = state.get("target_search_trends", {})
    yt = state.get("target_yt_trends", {})
    report = state.get("combined_final_cited_report", "")

    if isinstance(search, dict):
        search_list = search.get("target_search_trends", [])
    else:
        search_list = search if isinstance(search, list) else []

    if isinstance(yt, dict):
        yt_list = yt.get("target_yt_trends", [])
    else:
        yt_list = yt if isinstance(yt, list) else []

    print(f"\n--- State Check ---")
    print(f"  Search trends: {len(search_list)} selected")
    print(f"  YT trends: {len(yt_list)} selected")
    print(f"  Report: {len(str(report))} chars")

    return {
        "has_search_trends": len(search_list) > 0,
        "has_yt_trends": len(yt_list) > 0,
        "report_len": len(str(report)),
    }


def main():
    print(f"Testing GE interactive flow on engine {ENGINE_ID}")
    client = vertexai.Client(project=PROJECT, location=LOCATION)
    ae = client.agent_engines.get(name=RESOURCE_NAME)

    # Create session WITHOUT pre-populated trends
    session = ae.create_session(user_id=USER_ID, state=INITIAL_STATE)
    session_id = session.get("id") if isinstance(session, dict) else str(session)
    print(f"Session: {session_id}")

    # Step 1: Initial message — should trigger TRENDS stage with autopilot auto-selection
    stream_and_print(ae, "Run the full campaign pipeline for Tide Fabric Softener with Hibiscus Scent in autopilot mode.", session_id)
    state = check_state(ae, session_id)

    # Step 2+: Send "continue" until trends are populated and RESEARCH begins
    MAX_WAVES = 10
    for wave in range(MAX_WAVES):
        if state["has_search_trends"] and state["has_yt_trends"] and state["report_len"] > 0:
            print(f"\n*** SUCCESS: Trends populated AND research started! ***")
            break

        if state["has_search_trends"] and state["has_yt_trends"]:
            print(f"\n*** Trends populated — orchestrator should advance to RESEARCH ***")

        print(f"\n--- Wave {wave + 2} ---")
        stream_and_print(ae, "continue", session_id)
        state = check_state(ae, session_id)

    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"Search trends populated: {state['has_search_trends']}")
    print(f"YT trends populated: {state['has_yt_trends']}")
    print(f"Reached RESEARCH: {state['report_len'] > 0}")
    passed = state["has_search_trends"] and state["has_yt_trends"]
    print(f"TRENDS LOOP FIX: {'PASS' if passed else 'FAIL'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
