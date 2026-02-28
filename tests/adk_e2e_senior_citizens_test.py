"""
E2E test for trends_and_insights_agent via ADK web API.
Tests: McDonald's / McRib and Shamrock Shake / Senior Citizens / McRib and Shamrock is back forever

Focus: Full pipeline with auto trend selection, research, ad creative,
visual generation, AV editing studio (30s commercial), character consistency, and focus group evaluation.

Usage:
  Terminal 1: poetry run adk web trends_and_insights_agent
  Terminal 2: python tests/adk_e2e_senior_citizens_test.py
"""

import json
import subprocess
import time
import uuid
import requests
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

BASE_URL = "http://localhost:8000"
APP_NAME = "trends_and_insights_agent"
USER_ID = f"test-user-{uuid.uuid4().hex[:8]}"
SESSION_ID = None

# Timeouts in seconds
SHORT_TIMEOUT = 180
MEDIUM_TIMEOUT = 360
LONG_TIMEOUT = 600
EXTRA_LONG_TIMEOUT = 1200

# Tool names we track for diagnostic logging
TRACKED_TOOLS = {
    "generate_image", "generate_video",
    "save_img_artifact_key", "save_vid_artifact_key",
    "save_select_ad_copy", "save_select_visual_concept",
    "save_creatives_and_research_report",
    "ad_creative_pipeline", "visual_generation_pipeline", "visual_generator",
    "load_artifacts",
    "generate_subject_image", "generate_clip_with_frames",
    "extract_frame_from_clip", "concatenate_clips", "trim_video",
    "save_commercial_artifact", "analyze_commercial_video",
    "memorize",
    "get_daily_gtrends", "get_youtube_trends",
    "save_search_trends_to_session_state", "save_yt_trends_to_session_state",
}


def create_session():
    """Create a new session."""
    resp = requests.post(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
        json={"state": {}},
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"[SESSION] Created session: {data['id']}")
    return data["id"]


def send_message(session_id, message, timeout=SHORT_TIMEOUT):
    """Send a message and wait for the agent response. Returns (full_text, tool_calls_list)."""
    print(f"\n{'='*70}")
    print(f"[USER] {message[:200]}{'...' if len(message) > 200 else ''}")
    print(f"{'='*70}")

    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": message}],
        },
        "streaming": False,
    }

    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/run",
            json=payload,
            timeout=timeout,
        )
        elapsed = time.time() - start
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out after {timeout}s")
        return None, []
    except Exception as e:
        print(f"[ERROR] {e}")
        return None, []

    # Parse SSE response -- extract text and tool calls
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
                                artifact = fr_resp.get("artifact_key", "")
                                extra = f" artifact_key={artifact}" if artifact else ""
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
    """Get current session state."""
    resp = requests.get(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}",
    )
    resp.raise_for_status()
    return resp.json()


def check_state_key(session_id, key):
    """Check if a state key has been set."""
    session = get_session_state(session_id)
    state = session.get("state", {})
    value = state.get(key)
    if value and value != "" and value != {} and value != []:
        print(f"  [STATE] '{key}' is set")
        return True
    else:
        print(f"  [STATE] '{key}' is NOT set or empty")
        return False


def check_artifact_keys(session_id, key, inner_key):
    """Check that an artifact key dict has at least 1 entry."""
    session = get_session_state(session_id)
    state = session.get("state", {})
    outer = state.get(key, {})
    items = outer.get(inner_key, []) if isinstance(outer, dict) else []
    count = len(items)
    status = "PASS" if count > 0 else "FAIL"
    print(f"  [{status}] {key} -> {inner_key}: {count} entries")
    if count > 0:
        for i, entry in enumerate(items):
            ak = entry.get("artifact_key", "?")
            print(f"    [{i}] {ak}")
    return count


def verify_character_consistency(session_id):
    """Verify that the commercial has scene_descriptions referencing consistent characters."""
    print("\n\n--- CHARACTER CONSISTENCY VERIFICATION ---")
    session = get_session_state(session_id)
    state = session.get("state", {})
    commercial = state.get("commercial_artifact", {})
    metadata = commercial.get("metadata", {})
    scene_descriptions = metadata.get("scene_descriptions", [])

    if not scene_descriptions:
        print("  [FAIL] No scene_descriptions found in commercial_artifact metadata")
        return False

    print(f"  [INFO] Found {len(scene_descriptions)} scene descriptions")

    # Check if scene descriptions reference consistent characters
    # Look for common character references across scenes
    character_keywords = ["character", "person", "senior", "elderly", "customer", "protagonist"]
    scenes_with_characters = 0

    for i, scene in enumerate(scene_descriptions):
        scene_lower = scene.lower()
        has_character = any(keyword in scene_lower for keyword in character_keywords)
        if has_character:
            scenes_with_characters += 1
        print(f"  [{i+1}] {scene[:100]}{'...' if len(scene) > 100 else ''}")

    # Consider it consistent if at least 2 scenes reference characters
    is_consistent = scenes_with_characters >= 2
    print(f"  [{'PASS' if is_consistent else 'WARN'}] Character consistency: {scenes_with_characters}/{len(scene_descriptions)} scenes reference characters")

    return is_consistent


def verify_gcs_output(session_id):
    """Verify GCS bucket contains expected output files."""
    print("\n\n--- GCS VERIFICATION ---")
    session = get_session_state(session_id)
    state = session.get("state", {})
    gcs_folder = state.get("gcs_folder", "")

    if not gcs_folder:
        print("  [FAIL] gcs_folder not set in state")
        return False

    bucket = state.get("gcs_bucket", "")
    if not bucket:
        try:
            import os
            bucket = os.environ.get("BUCKET", "")
        except Exception:
            pass

    if not bucket:
        print("  [WARN] Could not determine GCS bucket, skipping GCS verification")
        return True

    if not bucket.startswith("gs://"):
        bucket = f"gs://{bucket}"

    gcs_path = f"{bucket}/{gcs_folder}/"
    print(f"  [INFO] Checking GCS path: {gcs_path}")

    try:
        result = subprocess.run(
            ["gsutil", "ls", gcs_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"  [WARN] gsutil ls failed: {result.stderr.strip()}")
            return False

        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        print(f"  [INFO] Found {len(files)} files in GCS folder")

        has_png = any(f.endswith(".png") for f in files)
        has_mp4 = any(f.endswith(".mp4") for f in files)
        has_final_pdf = any("final_trends_and_creatives_report.pdf" in f for f in files)

        for f in files:
            print(f"    {f}")

        print(f"  [{'PASS' if has_png else 'FAIL'}] .png image(s) in GCS")
        print(f"  [{'PASS' if has_mp4 else 'FAIL'}] .mp4 video(s) in GCS")
        print(f"  [{'PASS' if has_final_pdf else 'FAIL'}] final_trends_and_creatives_report.pdf in GCS")

        return has_png and has_mp4 and has_final_pdf
    except FileNotFoundError:
        print("  [WARN] gsutil not found, skipping GCS verification")
        return True
    except subprocess.TimeoutExpired:
        print("  [WARN] gsutil timed out")
        return False


def verify_focus_group_response(response):
    """Verify that the focus group response contains scoring and Go/No-Go recommendation."""
    if not response:
        print("  [FAIL] No response from focus group")
        return False

    response_lower = response.lower()

    # Check for scoring categories
    scoring_keywords = ["score", "rating", "evaluation", "assessment"]
    has_scoring = any(keyword in response_lower for keyword in scoring_keywords)

    # Check for Go/No-Go recommendation
    has_recommendation = ("go" in response_lower and "no-go" in response_lower) or \
                        ("recommend" in response_lower) or \
                        ("approval" in response_lower)

    print(f"  [{'PASS' if has_scoring else 'FAIL'}] Response contains scoring categories")
    print(f"  [{'PASS' if has_recommendation else 'FAIL'}] Response contains Go/No-Go recommendation")

    return has_scoring and has_recommendation


def main():
    print("=" * 70)
    print("ADK E2E Test: McDonald's / McRib and Shamrock Shake / Senior Citizens")
    print("Focus: Auto trend selection + AV studio + Character consistency + Focus group")
    print("=" * 70)

    # Step 0: Create session
    session_id = create_session()

    # ===================================================================
    # Step 1: Say hello
    # ===================================================================
    print("\n\n--- STEP 1: Greeting ---")
    response, tools = send_message(session_id, "hello", timeout=SHORT_TIMEOUT)
    if response is None:
        print("[FAIL] No response to greeting")
        sys.exit(1)

    if "KeyError" in (response or "") or "Context variable not found" in (response or ""):
        print("[FAIL] KeyError detected in greeting response!")
        sys.exit(1)
    print("[PASS] No KeyError in greeting response")

    # ===================================================================
    # Step 2: Provide campaign metadata
    # ===================================================================
    print("\n\n--- STEP 2: Campaign Metadata ---")
    response, tools = send_message(
        session_id,
        (
            "Brand: McDonald's, Product: McRib and Shamrock Shake, "
            "Audience: Senior Citizens, Key Selling Points: McRib and Shamrock is back forever"
        ),
        timeout=SHORT_TIMEOUT,
    )

    time.sleep(2)
    check_state_key(session_id, "brand")
    check_state_key(session_id, "target_product")
    check_state_key(session_id, "target_audience")
    check_state_key(session_id, "key_selling_points")

    # ===================================================================
    # Step 3: Auto-select trends
    # ===================================================================
    print("\n\n--- STEP 3: Auto-Select Trends ---")
    response, tools = send_message(
        session_id,
        (
            "Auto-select the best trends for this campaign. "
            "Pick brand-safe Google Search and YouTube trends "
            "relevant to McDonald's McRib and Shamrock Shake for Senior Citizens."
        ),
        timeout=MEDIUM_TIMEOUT,
    )

    # Check if trends were saved
    search_saved = check_state_key(session_id, "target_search_trends")
    yt_saved = check_state_key(session_id, "target_yt_trends")

    # Step 3b: Retry if trends not saved
    if not search_saved or not yt_saved:
        print("\n  [RETRY] Trends not fully saved, retrying...")
        retry_msg = "Please finish selecting and saving the trends. "
        if not search_saved:
            retry_msg += (
                "Use save_search_trends_to_session_state to save the best "
                "Google Search trend. "
            )
        if not yt_saved:
            retry_msg += (
                "Use save_yt_trends_to_session_state to save the best "
                "YouTube trending video. "
            )
        response, tools = send_message(session_id, retry_msg, timeout=MEDIUM_TIMEOUT)
        check_state_key(session_id, "target_search_trends")
        check_state_key(session_id, "target_yt_trends")

    # ===================================================================
    # Step 4: Confirm and proceed to research
    # ===================================================================
    print("\n\n--- STEP 4: Confirm Selections -> Research ---")
    response, tools = send_message(
        session_id,
        "Looks great, proceed with research.",
        timeout=LONG_TIMEOUT,
    )

    # Wait for research pipeline if needed
    if not check_state_key(session_id, "combined_final_cited_report"):
        print("  Waiting for research to complete...")
        response, tools = send_message(
            session_id,
            "Please continue with the research pipeline",
            timeout=LONG_TIMEOUT,
        )
        check_state_key(session_id, "combined_final_cited_report")

    # ===================================================================
    # Step 5: Proceed to ad generation
    # ===================================================================
    print("\n\n--- STEP 5: Report -> Ad Generation ---")
    response, tools = send_message(
        session_id,
        "Report looks good, proceed to ad generation.",
        timeout=LONG_TIMEOUT,
    )

    # Wait for ad creative pipeline
    if not check_state_key(session_id, "ad_copy_critique"):
        response, tools = send_message(
            session_id,
            "Please generate the ad copies",
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 6: Select ad copies
    # ===================================================================
    print("\n\n--- STEP 6: Select Ad Copies ---")
    response, tools = send_message(
        session_id,
        (
            "These ad copies look great. I want to select ad copies 1, 2, and 3. "
            "Please use the save_select_ad_copy tool to save each of these three "
            "ad copies one at a time."
        ),
        timeout=MEDIUM_TIMEOUT,
    )
    check_state_key(session_id, "final_select_ad_copies")

    if not check_state_key(session_id, "final_select_ad_copies"):
        print("  [WARN] Retrying ad copy selection...")
        response, tools = send_message(
            session_id,
            (
                "Please save ad copies 1, 2, and 3 using the save_select_ad_copy tool. "
                "Call save_select_ad_copy once for each ad copy."
            ),
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(session_id, "final_select_ad_copies")

    # ===================================================================
    # Step 7: Visual generation pipeline
    # ===================================================================
    print("\n\n--- STEP 7: Visual Generation Pipeline ---")
    response, tools = send_message(
        session_id,
        (
            "Great, the ad copies are saved. Now please proceed with step 4 of your "
            "workflow: call the visual_generation_pipeline tool to generate visual "
            "concepts for the selected ad copies."
        ),
        timeout=LONG_TIMEOUT,
    )

    # Wait for visual concepts
    if not check_state_key(session_id, "final_visual_concepts"):
        response, tools = send_message(
            session_id,
            "Please continue with the visual concept generation",
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 8: Select visual concepts (1 image + 1 video)
    # ===================================================================
    print("\n\n--- STEP 8: Select Visual Concepts ---")
    response, tools = send_message(
        session_id,
        (
            "I want to select visual concepts for generation. "
            "Please select and save 2 visual concepts using the save_select_visual_concept tool:\n"
            "- Select the first image-type concept from the list and save it with type 'image'\n"
            "- Select the first video-type concept from the list and save it with type 'video'\n"
            "Call save_select_visual_concept once for each concept, chaining the calls."
        ),
        timeout=MEDIUM_TIMEOUT,
    )
    check_state_key(session_id, "final_select_vis_concepts")

    if not check_state_key(session_id, "final_select_vis_concepts"):
        print("  [WARN] Retrying visual concept selection...")
        response, tools = send_message(
            session_id,
            (
                "Please use the save_select_visual_concept tool to save at least "
                "2 visual concepts: one with type 'image' and one with type 'video'. "
                "Call save_select_visual_concept once per concept."
            ),
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(session_id, "final_select_vis_concepts")

    # ===================================================================
    # Step 9: Generate visuals (Imagen + Veo)
    # ===================================================================
    print("\n\n--- STEP 9: Generate Visuals (Imagen + Veo) ---")
    response, tools = send_message(
        session_id,
        (
            "Now please proceed with step 6 of your workflow: call the visual_generator "
            "tool to generate the actual image and video creatives from the selected "
            "visual concepts in the 'final_select_vis_concepts' state key.\n\n"
            "The visual_generator sub-agent will use generate_image for image concepts "
            "and generate_video for video concepts.\n\n"
            "After the visual_generator completes:\n"
            "- For each image generated, call save_img_artifact_key with the artifact details\n"
            "- For each video generated, call save_vid_artifact_key with the artifact details\n\n"
            "This is the most important step -- please execute it now."
        ),
        timeout=LONG_TIMEOUT,
    )

    img_count = check_artifact_keys(session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(session_id, "vid_artifact_keys", "vid_artifact_keys")

    if img_count == 0 and vid_count == 0:
        print("\n  [RETRY] No artifacts saved, retrying...")
        response, tools = send_message(
            session_id,
            (
                "The visual generation step did not produce any artifacts. "
                "Please call the visual_generator tool now to generate the creatives. "
                "Then call save_img_artifact_key for each image and "
                "save_vid_artifact_key for each video that was generated."
            ),
            timeout=LONG_TIMEOUT,
        )
        img_count = check_artifact_keys(session_id, "img_artifact_keys", "img_artifact_keys")
        vid_count = check_artifact_keys(session_id, "vid_artifact_keys", "vid_artifact_keys")

    if img_count == 0:
        print("\n  [RETRY] No images yet, requesting image generation...")
        response, tools = send_message(
            session_id,
            (
                "Please generate at least one image now. Look at the image-type concepts "
                "in 'final_select_vis_concepts' and call the visual_generator tool "
                "which will use generate_image. After generation, call save_img_artifact_key."
            ),
            timeout=LONG_TIMEOUT,
        )
        img_count = check_artifact_keys(session_id, "img_artifact_keys", "img_artifact_keys")

    if vid_count == 0:
        print("\n  [RETRY] No videos yet, requesting video generation...")
        response, tools = send_message(
            session_id,
            (
                "Please generate at least one video now. Look at the video-type concepts "
                "in 'final_select_vis_concepts' and call the visual_generator tool "
                "which will use generate_video. After generation, call save_vid_artifact_key."
            ),
            timeout=LONG_TIMEOUT,
        )
        vid_count = check_artifact_keys(session_id, "vid_artifact_keys", "vid_artifact_keys")

    # ===================================================================
    # Step 10: Save creatives report
    # ===================================================================
    print("\n\n--- STEP 10: Save Creatives Report ---")
    response, tools = send_message(
        session_id,
        (
            "I'm satisfied with the generated creatives. "
            "As per step 4 of your workflow, please call the "
            "save_creatives_and_research_report tool now to build "
            "the final PDF report that includes the web research and ad creatives. "
            "Do not describe what you would do -- actually call the tool now."
        ),
        timeout=LONG_TIMEOUT,
    )

    if "save_creatives_and_research_report" not in tools:
        print("  [WARN] save_creatives_and_research_report not in tool calls, retrying...")
        response, tools = send_message(
            session_id,
            (
                "You need to call the save_creatives_and_research_report tool right now. "
                "This is step 4 in the root_agent workflow. Just call the tool -- "
                "do not explain, just execute it."
            ),
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 11: Transfer to AV Editing Studio for 30s commercial
    # ===================================================================
    # The AV studio pipeline is:
    #   1. Plan storyboard (4 scenes)
    #   2. Generate subject reference images
    #   3. Generate clips 1-4 with frame chaining (each takes ~2-5 min)
    #   4. Concatenate clips, trim to 30s, save commercial artifact
    #
    # We break this into granular sub-steps with generous timeouts
    # because Veo clip generation is long-running.
    # ===================================================================

    # --- Step 11a: Storyboard + Subject Images ---
    print("\n\n--- STEP 11a: Storyboard + Subject Images ---")
    response, tools = send_message(
        session_id,
        (
            "Now proceed to step 5: transfer to the av_editing_studio_agent sub-agent. "
            "The AV studio should produce a 30-second commercial. "
            "Start by planning the 4-scene storyboard for McRib and Shamrock Shake "
            "targeting Senior Citizens, connecting the selected trends to the product. "
            "Then call generate_subject_image for the primary character/product reference."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    has_subject = "generate_subject_image" in tools or "transfer_to_agent" in tools
    if not has_subject:
        print("  [INFO] Storyboard presented; nudging to generate subject images...")
        response, tools = send_message(
            session_id,
            (
                "The storyboard looks good. Now call generate_subject_image to create "
                "the primary character/product reference image. This image will be "
                "used as the first_frame_gcs_uri for Clip 1."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # --- Step 11b: Generate Clips 1 & 2 ---
    print("\n\n--- STEP 11b: Generate Clips 1 & 2 ---")
    response, tools = send_message(
        session_id,
        (
            "Now generate the first 2 clips of the commercial:\n"
            "1. Call generate_clip_with_frames for Clip 1 (Hook scene) using the "
            "subject image as first_frame_gcs_uri.\n"
            "2. Call extract_frame_from_clip on Clip 1 to get the last frame.\n"
            "3. Call generate_clip_with_frames for Clip 2 (Connection scene) using "
            "that last frame as first_frame_gcs_uri.\n"
            "Execute these now. Take your time -- each clip may take a few minutes."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    has_clips_12 = "generate_clip_with_frames" in tools
    if not has_clips_12:
        print("  [RETRY] Clips 1&2 not started, retrying...")
        response, tools = send_message(
            session_id,
            (
                "Please start generating Clip 1 now using generate_clip_with_frames. "
                "Use the subject image GCS URI as first_frame_gcs_uri. "
                "After Clip 1 finishes, extract its last frame and generate Clip 2."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # --- Step 11c: Generate Clips 3 & 4 ---
    print("\n\n--- STEP 11c: Generate Clips 3 & 4 ---")
    response, tools = send_message(
        session_id,
        (
            "Continue with Clips 3 and 4:\n"
            "1. Call extract_frame_from_clip on Clip 2 to get the last frame.\n"
            "2. Call generate_clip_with_frames for Clip 3 (Demonstration scene).\n"
            "3. Extract the last frame of Clip 3.\n"
            "4. Call generate_clip_with_frames for Clip 4 (Resolution scene).\n"
            "Execute these now."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    has_clips_34 = "generate_clip_with_frames" in tools or "extract_frame_from_clip" in tools
    if not has_clips_34:
        print("  [RETRY] Clips 3&4 not started, retrying...")
        response, tools = send_message(
            session_id,
            (
                "Please continue generating the remaining clips. Extract the last "
                "frame from the most recent clip and use it as first_frame_gcs_uri "
                "for the next clip. Generate clips until you have 4 total."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # --- Step 11d: Assembly (concatenate + trim + save) ---
    print("\n\n--- STEP 11d: Concatenate, Trim & Save ---")
    commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        # The agent has generated clips but hasn't assembled them.
        # Ask it to recall the clip URIs from its own conversation context.
        response, tools = send_message(
            session_id,
            (
                "You have generated all the clips. Now complete the final assembly:\n\n"
                "STEP 1: Call concatenate_clips with the GCS URIs of ALL the clips "
                "you generated (in scene order: Hook, Connection, Demonstration, Resolution). "
                "Use output_name='mcrib_senior_commercial'.\n\n"
                "STEP 2: Call trim_video on the concatenated video to exactly 30 seconds.\n\n"
                "STEP 3: Call save_commercial_artifact with:\n"
                "  - commercial_gcs_uri: the trimmed video GCS URI from step 2\n"
                "  - commercial_metadata: a dict with these keys:\n"
                "    - title: 'McRib & Shamrock Shake: Back Forever'\n"
                "    - scene_descriptions: list of 4 scene descriptions\n"
                "    - total_clips: 4\n"
                "    - duration_seconds: 30\n"
                "    - narrative_arc: summary of the commercial's story\n"
                "    - trend_connections: which trends informed the creative\n"
                "    - target_audience_appeal: why this resonates with Senior Citizens\n\n"
                "Execute all three tool calls now. Do not explain -- just call the tools."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        print("  [RETRY] Assembly not complete, retrying...")
        response, tools = send_message(
            session_id,
            (
                "The commercial artifact has NOT been saved yet. You must:\n"
                "1. Call concatenate_clips with all clip GCS URIs\n"
                "2. Call trim_video to 30 seconds\n"
                "3. Call save_commercial_artifact\n\n"
                "Look back at your previous generate_clip_with_frames responses "
                "to find the GCS URIs. Then call the tools. Do it now."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        print("  [RETRY] Second retry -- just requesting save...")
        response, tools = send_message(
            session_id,
            (
                "If you have already concatenated and trimmed the video, "
                "call save_commercial_artifact now with the GCS URI and "
                "metadata including duration_seconds=30. "
                "If not, start by calling concatenate_clips first."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(session_id, "commercial_artifact")

    # Verify duration is 30 seconds
    if commercial_saved:
        session = get_session_state(session_id)
        state = session.get("state", {})
        commercial = state.get("commercial_artifact", {})
        metadata = commercial.get("metadata", {})
        duration = metadata.get("duration_seconds", 0)
        print(f"  [{'PASS' if duration == 30 else 'WARN'}] commercial duration: {duration}s (expected 30)")

    # ===================================================================
    # Step 11d: Character Consistency Verification
    # ===================================================================
    character_consistency = verify_character_consistency(session_id)

    # ===================================================================
    # Step 12: Transfer to Focus Group Evaluator
    # ===================================================================
    print("\n\n--- STEP 12: Focus Group Evaluator ---")
    response, tools = send_message(
        session_id,
        (
            "Now proceed to step 6: transfer to the focus_group_evaluator_agent "
            "sub-agent. It should call the analyze_commercial_video tool to analyze "
            "the 30-second commercial, then simulate a focus group panel with scoring "
            "categories and a Go/No-Go recommendation."
        ),
        timeout=LONG_TIMEOUT,
    )

    # Check if analyze_commercial_video was called
    analyze_called = "analyze_commercial_video" in tools
    print(f"  [{'PASS' if analyze_called else 'WARN'}] analyze_commercial_video called: {analyze_called}")

    if not analyze_called:
        print("  [RETRY] Asking focus group to analyze the commercial...")
        response, tools = send_message(
            session_id,
            (
                "You are the focus_group_evaluator_agent. Call the "
                "analyze_commercial_video tool now to analyze the commercial "
                "video stored in session state. Then provide the full focus "
                "group evaluation with scores and a Go/No-Go recommendation."
            ),
            timeout=LONG_TIMEOUT,
        )
        analyze_called = "analyze_commercial_video" in tools
        print(f"  [{'PASS' if analyze_called else 'WARN'}] analyze_commercial_video called (retry): {analyze_called}")

    # Verify focus group response has scoring and Go/No-Go
    focus_group_valid = verify_focus_group_response(response)

    # ===================================================================
    # GCS Verification
    # ===================================================================
    gcs_pass = verify_gcs_output(session_id)

    # ===================================================================
    # Step 13: Final State Verification
    # ===================================================================
    print("\n\n" + "=" * 70)
    print("FINAL STATE VERIFICATION")
    print("=" * 70)
    session = get_session_state(session_id)
    state = session.get("state", {})

    # Required campaign keys
    required_keys = [
        "brand", "target_product", "target_audience", "key_selling_points",
        "target_search_trends", "target_yt_trends",
    ]

    all_pass = True
    for key in required_keys:
        val = state.get(key, "")
        is_set = val and val != "" and val != {} and val != []
        status = "PASS" if is_set else "FAIL"
        if not is_set:
            all_pass = False
        print(f"  [{status}] {key}")

    # Pipeline state keys
    pipeline_keys = [
        "combined_final_cited_report",
        "ad_copy_critique",
        "final_select_ad_copies",
        "final_visual_concepts",
        "final_select_vis_concepts",
    ]
    for key in pipeline_keys:
        val = state.get(key, "")
        is_set = val and val != "" and val != {} and val != []
        status = "PASS" if is_set else "WARN"
        print(f"  [{status}] {key}")

    # Artifact keys
    img_count = check_artifact_keys(session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(session_id, "vid_artifact_keys", "vid_artifact_keys")

    img_pass = img_count > 0
    vid_pass = vid_count > 0

    if not img_pass:
        all_pass = False
    if not vid_pass:
        all_pass = False

    # Commercial artifact check
    commercial = state.get("commercial_artifact", {})
    commercial_pass = bool(commercial and commercial.get("artifact_key"))
    commercial_duration = commercial.get("metadata", {}).get("duration_seconds", 0)
    duration_pass = commercial_duration == 30
    print(f"  [{'PASS' if commercial_pass else 'FAIL'}] commercial_artifact")
    print(f"  [{'PASS' if duration_pass else 'WARN'}] commercial_artifact.duration_seconds == 30 (actual: {commercial_duration})")
    print(f"  [{'PASS' if character_consistency else 'WARN'}] character_consistency in scene_descriptions")
    print(f"  [{'PASS' if focus_group_valid else 'WARN'}] focus_group response has scoring and Go/No-Go")

    print(f"\n  [{'PASS' if gcs_pass else 'FAIL'}] GCS output verification")

    # Summary
    print(f"\n{'='*70}")
    if all_pass and img_pass and vid_pass and commercial_pass and gcs_pass:
        print("E2E TEST: FULL PIPELINE PASSED")
        print(f"  Images generated: {img_count}")
        print(f"  Videos generated: {vid_count}")
        print(f"  Commercial: {commercial_duration}s")
        print(f"  Character consistency: {character_consistency}")
        print(f"  Focus group valid: {focus_group_valid}")
        print(f"  GCS verified: {gcs_pass}")
    elif all_pass and (img_pass or vid_pass):
        print("E2E TEST: PARTIAL PASS (some creatives generated)")
        print(f"  Images: {img_count} ({'PASS' if img_pass else 'MISSING'})")
        print(f"  Videos: {vid_count} ({'PASS' if vid_pass else 'MISSING'})")
        print(f"  Commercial: {'PASS' if commercial_pass else 'MISSING'} ({commercial_duration}s)")
        print(f"  Character consistency: {character_consistency}")
        print(f"  Focus group valid: {focus_group_valid}")
        print(f"  GCS verified: {gcs_pass}")
    else:
        print("E2E TEST: SOME CHECKS FAILED (see above)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
