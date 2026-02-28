"""
Standalone AV Studio E2E test.
Skips steps 1-10 by pre-populating session state, then tests only the AV studio
pipeline: storyboard -> subject images -> clip generation -> concat -> trim -> save.

Usage:
  Terminal 1: poetry run adk web .
  Terminal 2: python tests/adk_av_studio_test.py
"""

import json
import time
import uuid
import requests
import sys

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

BASE_URL = "http://localhost:8000"
APP_NAME = "trends_and_insights_agent"
USER_ID = f"test-av-{uuid.uuid4().hex[:8]}"

# Timeouts
SHORT_TIMEOUT = 180
LONG_TIMEOUT = 600
EXTRA_LONG_TIMEOUT = 1200

# Pre-populated session state to skip steps 1-10
PREFILLED_STATE = {
    "brand": "McDonald's",
    "target_product": "McRib and Shamrock Shake",
    "target_audience": "Senior Citizens",
    "key_selling_points": "McRib and Shamrock is back forever",
    "target_search_trends": {
        "target_search_trends": [
            {"keyword": "McRib back 2026", "description": "Trending search about McRib returning permanently"}
        ]
    },
    "target_yt_trends": {
        "target_yt_trends": [
            {"title": "McRib is BACK FOREVER", "description": "Viral video about McRib permanent return"}
        ]
    },
    "combined_final_cited_report": (
        "Research Report: McDonald's McRib and Shamrock Shake campaign targeting Senior Citizens. "
        "Key findings: (1) Nostalgia is the #1 driver for seniors engaging with fast food brands. "
        "(2) McRib has a cult following among 55+ demographic who remember its original 1981 launch. "
        "(3) Shamrock Shake evokes St. Patrick's Day traditions and seasonal comfort. "
        "(4) Seniors respond best to warm, family-oriented imagery with slow pacing. "
        "(5) The 'back forever' messaging resonates as permanence and reliability."
    ),
    "ad_copy_critique": "Ad copies reviewed and approved.",
    "final_select_ad_copies": {
        "final_select_ad_copies": [
            {
                "headline": "Some Things Get Better With Time",
                "body": "The McRib and Shamrock Shake are back - this time forever. Join the celebration.",
                "cta": "Visit McDonald's Today",
                "tone": "warm, nostalgic, celebratory",
            }
        ]
    },
    "final_visual_concepts": "Visual concepts generated.",
    "final_select_vis_concepts": {
        "final_select_vis_concepts": [
            {
                "concept": "A warm McDonald's restaurant scene with a senior couple sharing McRib and Shamrock Shake",
                "type": "image",
                "mood": "nostalgic, warm, golden hour lighting",
            }
        ]
    },
    "img_artifact_keys": {"img_artifact_keys": []},
    "vid_artifact_keys": {"vid_artifact_keys": []},
}

TRACKED_TOOLS = {
    "generate_subject_image", "generate_clip_with_frames",
    "extract_frame_from_clip", "concatenate_clips", "trim_video",
    "save_commercial_artifact", "analyze_commercial_video",
    "transfer_to_agent",
}


def create_session():
    """Create a session pre-populated with state from steps 1-10."""
    resp = requests.post(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
        json={"state": PREFILLED_STATE},
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"[SESSION] Created pre-populated session: {data['id']}")
    return data["id"]


def send_message(session_id, message, timeout=SHORT_TIMEOUT):
    """Send a message and return (full_text, tool_calls_list)."""
    print(f"\n{'='*70}")
    print(f"[USER] {message[:200]}{'...' if len(message) > 200 else ''}")
    print(f"{'='*70}")

    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False,
    }

    start = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/run", json=payload, timeout=timeout)
        elapsed = time.time() - start
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timed out after {timeout}s")
        return None, []
    except Exception as e:
        print(f"[ERROR] {e}")
        return None, []

    response_texts = []
    tool_calls = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            try:
                event_data = json.loads(line[5:].strip())
                if "content" in event_data and "parts" in event_data["content"]:
                    for part in event_data["content"]["parts"]:
                        if "text" in part and part["text"]:
                            response_texts.append(part["text"])
                        if "function_call" in part:
                            fc = part["function_call"]
                            tool_name = fc.get("name", "unknown")
                            tool_calls.append(tool_name)
                            marker = " ***" if tool_name in TRACKED_TOOLS else ""
                            print(f"  [TOOL] {tool_name}{marker}")
                        if "function_response" in part:
                            fr = part["function_response"]
                            fr_name = fr.get("name", "unknown")
                            fr_resp = fr.get("response", {})
                            if fr_name in TRACKED_TOOLS:
                                status = fr_resp.get("status", "")
                                gcs = fr_resp.get("gcs_uri", "")
                                extra = f" gcs_uri={gcs}" if gcs else ""
                                print(f"  [TOOL_RESP] {fr_name}: status={status}{extra}")
            except json.JSONDecodeError:
                pass

    full_response = "\n".join(response_texts)
    display = full_response[:2000] + "..." if len(full_response) > 2000 else full_response
    print(f"\n[AGENT] ({elapsed:.1f}s) {display}")
    if tool_calls:
        print(f"  [TOOLS CALLED] {', '.join(tool_calls)}")
    return full_response, tool_calls


def get_session_state(session_id):
    resp = requests.get(f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}")
    resp.raise_for_status()
    return resp.json()


def check_state_key(session_id, key):
    session = get_session_state(session_id)
    state = session.get("state", {})
    value = state.get(key)
    if value and value != "" and value != {} and value != []:
        print(f"  [STATE] '{key}' is set")
        return True
    else:
        print(f"  [STATE] '{key}' is NOT set or empty")
        return False


def main():
    print("=" * 70)
    print("AV STUDIO STANDALONE TEST")
    print("McDonald's / McRib + Shamrock Shake / Senior Citizens / 30s Commercial")
    print("=" * 70)

    session_id = create_session()

    # Verify pre-populated state
    print("\n--- Verifying pre-populated state ---")
    for key in ["brand", "target_product", "target_audience", "key_selling_points",
                "target_search_trends", "target_yt_trends", "combined_final_cited_report",
                "final_select_ad_copies", "final_select_vis_concepts"]:
        check_state_key(session_id, key)

    # ===================================================================
    # Step 1: Transfer to AV Studio + Storyboard + Subject Images
    # ===================================================================
    print("\n\n--- STEP 1: Storyboard + Subject Images ---")
    response, tools = send_message(
        session_id,
        (
            "Transfer to the av_editing_studio_agent sub-agent now. "
            "The AV studio should produce a 30-second commercial for McRib and "
            "Shamrock Shake targeting Senior Citizens. "
            "Start by planning a 4-scene storyboard connecting the trending topics "
            "to the product, then call generate_subject_image for the primary "
            "character and product reference."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    has_subject = "generate_subject_image" in tools or "transfer_to_agent" in tools
    if not has_subject:
        print("  [INFO] Nudging to generate subject images...")
        response, tools = send_message(
            session_id,
            (
                "Good storyboard. Now call generate_subject_image to create "
                "reference images for the primary character (a senior citizen) "
                "and the McRib/Shamrock Shake products."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # Check if AFC already completed the full pipeline in Step 1
    commercial_saved = check_state_key(session_id, "commercial_artifact")

    if commercial_saved:
        print("\n  [SKIP] AFC completed full pipeline in Step 1 - skipping Steps 2-4")
    else:
        # ===================================================================
        # Step 2: Generate Clips 1 & 2
        # ===================================================================
        print("\n\n--- STEP 2: Generate Clips 1 & 2 ---")
        response, tools = send_message(
            session_id,
            (
                "Now generate the first 2 clips:\n"
                "1. Call generate_clip_with_frames for Clip 1 (Hook scene) using "
                "the subject image as first_frame_gcs_uri.\n"
                "2. Call extract_frame_from_clip on Clip 1 to get the last frame.\n"
                "3. Call generate_clip_with_frames for Clip 2 (Connection scene) "
                "using Clip 1's last frame as first_frame_gcs_uri.\n"
                "Execute now."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

        if "generate_clip_with_frames" not in tools:
            print("  [RETRY] Clips not started, retrying...")
            response, tools = send_message(
                session_id,
                (
                    "Please start generating Clip 1 now using generate_clip_with_frames. "
                    "Use the subject image GCS URI as first_frame_gcs_uri."
                ),
                timeout=EXTRA_LONG_TIMEOUT,
            )

        # ===================================================================
        # Step 3: Generate Clips 3 & 4
        # ===================================================================
        print("\n\n--- STEP 3: Generate Clips 3 & 4 ---")
        response, tools = send_message(
            session_id,
            (
                "Continue with Clips 3 and 4:\n"
                "1. Extract the last frame of Clip 2.\n"
                "2. Generate Clip 3 (Demonstration scene).\n"
                "3. Extract the last frame of Clip 3.\n"
                "4. Generate Clip 4 (Resolution scene).\n"
                "Execute now."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

        if "generate_clip_with_frames" not in tools and "extract_frame_from_clip" not in tools:
            print("  [RETRY] Clips 3&4 not started, retrying...")
            response, tools = send_message(
                session_id,
                "Continue generating remaining clips with frame chaining until you have 4 total.",
                timeout=EXTRA_LONG_TIMEOUT,
            )

    # ===================================================================
    # Step 4: Concatenate + Trim + Save
    # ===================================================================
    print("\n\n--- STEP 4: Concatenate, Trim & Save ---")
    commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        response, tools = send_message(
            session_id,
            (
                "All clips are generated. Now complete the assembly:\n"
                "1. Call concatenate_clips with all 4 clip GCS URIs in scene order.\n"
                "2. Call trim_video to exactly 30 seconds.\n"
                "3. Call save_commercial_artifact with the trimmed video GCS URI "
                "and commercial_metadata dict containing:\n"
                "   - title: 'McRib & Shamrock Shake: Back Forever'\n"
                "   - scene_descriptions: list of 4 scene descriptions\n"
                "   - total_clips: 4\n"
                "   - duration_seconds: 30\n"
                "   - narrative_arc: summary of the story\n"
                "   - trend_connections: which trends informed the creative\n"
                "   - target_audience_appeal: why this resonates with Senior Citizens\n\n"
                "IMPORTANT: Use save_commercial_artifact (NOT save_vid_artifact_key). "
                "Execute all three tool calls now."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        print("  [RETRY] Assembly incomplete, retrying...")
        response, tools = send_message(
            session_id,
            (
                "The commercial_artifact is NOT saved yet. "
                "Call concatenate_clips, then trim_video to 30s, then "
                "save_commercial_artifact. Do it now."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        print("  [RETRY] Final attempt...")
        response, tools = send_message(
            session_id,
            (
                "Call save_commercial_artifact now with the trimmed video GCS URI "
                "and metadata dict. Include duration_seconds=30."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(session_id, "commercial_artifact")

    # ===================================================================
    # Step 5: Focus Group Evaluation
    # ===================================================================
    print("\n\n--- STEP 5: Focus Group Evaluation ---")
    if commercial_saved:
        response, tools = send_message(
            session_id,
            (
                "Transfer to the focus_group_evaluator_agent sub-agent. "
                "It should call analyze_commercial_video to analyze the 30-second "
                "commercial, then simulate a focus group with scoring and Go/No-Go."
            ),
            timeout=LONG_TIMEOUT,
        )

        if "analyze_commercial_video" not in tools:
            response, tools = send_message(
                session_id,
                "Call analyze_commercial_video now and provide the focus group evaluation.",
                timeout=LONG_TIMEOUT,
            )
    else:
        print("  [SKIP] No commercial_artifact to evaluate")

    # ===================================================================
    # Final Verification
    # ===================================================================
    print("\n\n" + "=" * 70)
    print("FINAL VERIFICATION")
    print("=" * 70)

    session = get_session_state(session_id)
    state = session.get("state", {})

    # Check vid_artifact_keys for generated clips
    vid_keys = state.get("vid_artifact_keys", {}).get("vid_artifact_keys", [])
    print(f"  Videos generated: {len(vid_keys)}")
    for i, v in enumerate(vid_keys):
        print(f"    [{i}] {v.get('artifact_key', '?')}")

    # Check commercial artifact
    commercial = state.get("commercial_artifact", {})
    has_commercial = bool(commercial and commercial.get("artifact_key"))
    duration = commercial.get("metadata", {}).get("duration_seconds", 0) if isinstance(commercial, dict) else 0

    print(f"\n  [{'PASS' if has_commercial else 'FAIL'}] commercial_artifact saved")
    print(f"  [{'PASS' if duration == 30 else 'WARN'}] duration: {duration}s (target: 30s)")

    if has_commercial:
        metadata = commercial.get("metadata", {})
        scenes = metadata.get("scene_descriptions", [])
        arc = metadata.get("narrative_arc", "")
        trends = metadata.get("trend_connections", "")
        appeal = metadata.get("target_audience_appeal", "")
        print(f"  [{'PASS' if len(scenes) >= 4 else 'WARN'}] scene_descriptions: {len(scenes)}")
        print(f"  [{'PASS' if arc else 'WARN'}] narrative_arc: {'set' if arc else 'missing'}")
        print(f"  [{'PASS' if trends else 'WARN'}] trend_connections: {'set' if trends else 'missing'}")
        print(f"  [{'PASS' if appeal else 'WARN'}] target_audience_appeal: {'set' if appeal else 'missing'}")
        print(f"\n  GCS URI: {commercial.get('gcs_uri', 'N/A')}")

    print(f"\n{'='*70}")
    if has_commercial and duration == 30:
        print("AV STUDIO TEST: PASSED")
    elif has_commercial:
        print("AV STUDIO TEST: PARTIAL PASS (commercial saved but duration != 30)")
    else:
        print("AV STUDIO TEST: FAILED (commercial_artifact not saved)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
