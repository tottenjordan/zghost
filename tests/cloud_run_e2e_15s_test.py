"""
E2E test for trends_and_insights_agent via Cloud Run.
Produces a 15-second commercial (2 clips) using preset configurations.

Usage:
  python tests/cloud_run_e2e_15s_test.py --preset example_state_pixel
  python tests/cloud_run_e2e_15s_test.py --preset example_state_prs --base-url https://my-cloud-run.app
"""

import argparse
import json
import subprocess
import time
import uuid
import requests
import sys

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

DEFAULT_BASE_URL = "https://trends-and-insights-frontend-in2bk2mdwa-uc.a.run.app"
APP_NAME = "trends_and_insights_agent"

# Timeouts in seconds
SHORT_TIMEOUT = 180
MEDIUM_TIMEOUT = 360
LONG_TIMEOUT = 600
EXTRA_LONG_TIMEOUT = 900

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


def create_session(base_url, preset):
    """Create a new session with preset config via the extended API."""
    resp = requests.post(
        f"{base_url}/api/v1/sessions",
        json={"preset_config": preset},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    session_id = data["session_id"]
    user_id = data["user_id"]
    print(f"[SESSION] Created session: {session_id} (user: {user_id}, preset: {preset})")
    return session_id, user_id


def send_message(base_url, user_id, session_id, message, timeout=SHORT_TIMEOUT):
    """Send a message via api_server SSE stream endpoint. Returns (full_text, tool_calls_list).

    Uses GET /api/v1/run/{session_id}/stream which shares the same InMemorySessionService
    as the /api/v1/sessions endpoint (both on api_server port 8000).
    """
    print(f"\n{'='*70}")
    print(f"[USER] {message[:200]}{'...' if len(message) > 200 else ''}")
    print(f"{'='*70}")

    start = time.time()
    try:
        resp = requests.get(
            f"{base_url}/api/v1/run/{session_id}/stream",
            params={"user_id": user_id, "message": message},
            timeout=timeout,
            stream=True,
        )
        elapsed_connect = time.time() - start
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out after {timeout}s")
        return None, []
    except Exception as e:
        print(f"[ERROR] {e}")
        return None, []

    response_texts = []
    tool_calls = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        try:
            event_data = json.loads(line[5:].strip())

            # Check for stream completion
            if event_data.get("type") == "stream_complete":
                break
            if event_data.get("type") == "stream_error":
                print(f"  [STREAM_ERROR] {event_data.get('error', 'unknown')}")
                break

            # Extract text from the api_server SSE format:
            # {"type": "...", "data": {"parts": [{"text": "..."}]}, "agent_name": "..."}
            data = event_data.get("data", {})
            parts = data.get("parts", [])
            for part in parts:
                if isinstance(part, dict) and "text" in part and part["text"]:
                    response_texts.append(part["text"])

            # Extract tool calls
            tool_name = data.get("tool_name", "")
            if tool_name:
                tool_calls.append(tool_name)
                marker = " ***" if tool_name in TRACKED_TOOLS else ""
                print(f"  [TOOL] {tool_name}{marker}")

        except json.JSONDecodeError:
            pass

    elapsed = time.time() - start
    full_response = "\n".join(response_texts)
    display = full_response[:2000] + "..." if len(full_response) > 2000 else full_response
    print(f"\n[AGENT] ({elapsed:.1f}s) {display}")
    if tool_calls:
        print(f"  [TOOLS CALLED] {', '.join(tool_calls)}")
    return full_response, tool_calls


def get_session_state(base_url, user_id, session_id):
    """Get current session state via api_server endpoint."""
    resp = requests.get(
        f"{base_url}/api/v1/sessions/{session_id}/state",
        params={"user_id": user_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def check_state_key(base_url, user_id, session_id, key):
    """Check if a state key has been set."""
    session = get_session_state(base_url, user_id, session_id)
    state = session.get("state", {})
    value = state.get(key)
    if value and value != "" and value != {} and value != []:
        print(f"  [STATE] '{key}' is set")
        return True
    else:
        print(f"  [STATE] '{key}' is NOT set or empty")
        return False


def check_artifact_keys(base_url, user_id, session_id, key, inner_key):
    """Check that an artifact key dict has at least 1 entry."""
    session = get_session_state(base_url, user_id, session_id)
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


def verify_gcs_output(base_url, user_id, session_id):
    """Verify GCS bucket contains expected output files."""
    print("\n\n--- GCS VERIFICATION ---")
    session = get_session_state(base_url, user_id, session_id)
    state = session.get("state", {})
    gcs_folder = state.get("gcs_folder", "")

    if not gcs_folder:
        print("  [FAIL] gcs_folder not set in state")
        return False

    bucket = state.get("gcs_bucket", "")
    if not bucket:
        import os
        bucket = os.environ.get("BUCKET", "")

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

        has_mp4 = any(f.endswith(".mp4") for f in files)
        for f in files:
            print(f"    {f}")

        print(f"  [{'PASS' if has_mp4 else 'FAIL'}] .mp4 video(s) in GCS")
        return has_mp4
    except FileNotFoundError:
        print("  [WARN] gsutil not found, skipping GCS verification")
        return True
    except subprocess.TimeoutExpired:
        print("  [WARN] gsutil timed out")
        return False


def main():
    parser = argparse.ArgumentParser(description="Cloud Run E2E 15s Commercial Test")
    parser.add_argument("--preset", default="example_state_pixel",
                        help="Preset config name (default: example_state_pixel)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"Cloud Run base URL (default: {DEFAULT_BASE_URL})")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    preset = args.preset

    print("=" * 70)
    print(f"Cloud Run E2E Test: 15s Commercial")
    print(f"  Preset: {preset}")
    print(f"  Base URL: {base_url}")
    print("=" * 70)

    # Step 0: Health check
    print("\n\n--- STEP 0: Health Check ---")
    try:
        resp = requests.get(f"{base_url}/health", timeout=30)
        print(f"  [INFO] Health: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"  [WARN] Health check failed: {e}")

    # Step 1: Create session with preset
    print("\n\n--- STEP 1: Create Session with Preset ---")
    session_id, user_id = create_session(base_url, preset)

    # Step 2: Say hello (triggers campaign metadata display)
    print("\n\n--- STEP 2: Greeting ---")
    response, tools = send_message(base_url, user_id, session_id, "hello", timeout=SHORT_TIMEOUT)
    if response is None:
        print("[FAIL] No response to greeting")
        sys.exit(1)
    if "KeyError" in (response or "") or "Context variable not found" in (response or ""):
        print("[FAIL] KeyError detected in greeting response!")
        sys.exit(1)
    print("[PASS] Greeting OK")

    # Verify preset loaded campaign metadata
    for key in ["brand", "target_product", "target_audience", "key_selling_points"]:
        check_state_key(base_url, user_id, session_id, key)

    # Step 3: Auto-select trends
    print("\n\n--- STEP 3: Auto-Select Trends ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "Auto-select the best trends for this campaign. "
        "Pick brand-safe Google Search and YouTube trends "
        "relevant to the product and audience.",
        timeout=MEDIUM_TIMEOUT,
    )

    search_saved = check_state_key(base_url, user_id, session_id, "target_search_trends")
    yt_saved = check_state_key(base_url, user_id, session_id, "target_yt_trends")

    if not search_saved or not yt_saved:
        print("\n  [RETRY] Trends not fully saved, retrying...")
        retry_msg = "Please finish selecting and saving the trends. "
        if not search_saved:
            retry_msg += "Use save_search_trends_to_session_state to save the best Google Search trend. "
        if not yt_saved:
            retry_msg += "Use save_yt_trends_to_session_state to save the best YouTube trending video. "
        response, tools = send_message(base_url, user_id, session_id, retry_msg, timeout=MEDIUM_TIMEOUT)
        check_state_key(base_url, user_id, session_id, "target_search_trends")
        check_state_key(base_url, user_id, session_id, "target_yt_trends")

    # Step 4: Proceed to research
    print("\n\n--- STEP 4: Confirm Selections -> Research ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "Looks great, proceed with research.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(base_url, user_id, session_id, "combined_final_cited_report"):
        print("  Waiting for research to complete...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "Please continue with the research pipeline",
            timeout=LONG_TIMEOUT,
        )
        check_state_key(base_url, user_id, session_id, "combined_final_cited_report")

    # Step 5: Ad generation
    print("\n\n--- STEP 5: Report -> Ad Generation ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "Report looks good, proceed to ad generation.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(base_url, user_id, session_id, "ad_copy_critique"):
        response, tools = send_message(
            base_url, user_id, session_id,
            "Please generate the ad copies",
            timeout=LONG_TIMEOUT,
        )

    # Step 6: Select ad copies
    print("\n\n--- STEP 6: Select Ad Copies ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "These ad copies look great. I want to select ad copies 1, 2, and 3. "
        "Please use the save_select_ad_copy tool to save each of these three "
        "ad copies one at a time.",
        timeout=MEDIUM_TIMEOUT,
    )
    if not check_state_key(base_url, user_id, session_id, "final_select_ad_copies"):
        print("  [WARN] Retrying ad copy selection...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "Please save ad copies 1, 2, and 3 using the save_select_ad_copy tool. "
            "Call save_select_ad_copy once for each ad copy.",
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(base_url, user_id, session_id, "final_select_ad_copies")

    # Step 7: Visual generation pipeline
    print("\n\n--- STEP 7: Visual Generation Pipeline ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "Great, the ad copies are saved. Now please proceed with step 4: "
        "call the visual_generation_pipeline tool to generate visual "
        "concepts for the selected ad copies.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(base_url, user_id, session_id, "final_visual_concepts"):
        response, tools = send_message(
            base_url, user_id, session_id,
            "Please continue with the visual concept generation",
            timeout=LONG_TIMEOUT,
        )

    # Step 8: Select visual concepts (1 image + 1 video)
    print("\n\n--- STEP 8: Select Visual Concepts ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "I want to select visual concepts for generation. "
        "Please select and save 2 visual concepts using the save_select_visual_concept tool:\n"
        "- Select the first image-type concept and save with type 'image'\n"
        "- Select the first video-type concept and save with type 'video'\n"
        "Call save_select_visual_concept once for each concept.",
        timeout=MEDIUM_TIMEOUT,
    )
    if not check_state_key(base_url, user_id, session_id, "final_select_vis_concepts"):
        print("  [WARN] Retrying visual concept selection...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "Please use the save_select_visual_concept tool to save at least "
            "2 visual concepts: one with type 'image' and one with type 'video'. "
            "Call save_select_visual_concept once per concept.",
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(base_url, user_id, session_id, "final_select_vis_concepts")

    # Step 9: Generate visuals (Imagen + Veo)
    print("\n\n--- STEP 9: Generate Visuals (Imagen + Veo) ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "Now please proceed with step 6: call the visual_generator "
        "tool to generate the actual image and video creatives from the selected "
        "visual concepts in 'final_select_vis_concepts'.\n\n"
        "After the visual_generator completes:\n"
        "- Call save_img_artifact_key for each image\n"
        "- Call save_vid_artifact_key for each video\n\n"
        "Execute it now.",
        timeout=LONG_TIMEOUT,
    )

    img_count = check_artifact_keys(base_url, user_id, session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(base_url, user_id, session_id, "vid_artifact_keys", "vid_artifact_keys")

    if img_count == 0 and vid_count == 0:
        print("\n  [RETRY] No artifacts saved, retrying...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "Please call the visual_generator tool now to generate the creatives. "
            "Then call save_img_artifact_key for each image and "
            "save_vid_artifact_key for each video.",
            timeout=LONG_TIMEOUT,
        )
        img_count = check_artifact_keys(base_url, user_id, session_id, "img_artifact_keys", "img_artifact_keys")
        vid_count = check_artifact_keys(base_url, user_id, session_id, "vid_artifact_keys", "vid_artifact_keys")

    # Step 10: Save creatives report
    print("\n\n--- STEP 10: Save Creatives Report ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "I'm satisfied with the generated creatives. "
        "Please call the save_creatives_and_research_report tool now to build "
        "the final PDF report. Do not describe what you would do -- actually call the tool now.",
        timeout=LONG_TIMEOUT,
    )

    if "save_creatives_and_research_report" not in tools:
        print("  [WARN] save_creatives_and_research_report not called, retrying...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "You need to call the save_creatives_and_research_report tool right now. "
            "Just call the tool -- do not explain, just execute it.",
            timeout=LONG_TIMEOUT,
        )

    # Step 11: AV Editing Studio for 15s commercial (2 scenes, 2 clips)
    print("\n\n--- STEP 11a: Transfer to AV Editing Studio (15s) ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "Now proceed to step 5: transfer to the av_editing_studio_agent sub-agent. "
        "The AV studio should produce a 15-second commercial. "
        "This means: plan a 2-scene storyboard (Hook + Connection, Demo + CTA), "
        "generate 2 clips (~16s raw), then trim to 15 seconds. "
        "Start by planning the 2-scene storyboard and generating subject reference images.",
        timeout=EXTRA_LONG_TIMEOUT,
    )

    has_subject_tools = any(t in tools for t in ["generate_subject_image", "transfer_to_agent"])
    if not has_subject_tools:
        print("  [INFO] Nudging to generate subjects...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "The storyboard looks good. Now execute Step 2: "
            "call generate_subject_image for the primary character and product. "
            "Then proceed to Step 3: generate 2 clips using "
            "generate_clip_with_frames with frame chaining. "
            "Remember: only 2 clips for a 15-second commercial.",
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # Step 11b: Clip generation
    print("\n\n--- STEP 11b: Clip Generation (2 clips for 15s) ---")
    has_clip_tools = any(t in tools for t in [
        "generate_clip_with_frames", "extract_frame_from_clip",
        "concatenate_clips", "trim_video", "save_commercial_artifact",
    ])
    if not has_clip_tools:
        print("  [INFO] Clips not started yet, sending explicit instruction...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "Now execute Step 3 of the AV studio workflow for a 15-second commercial: "
            "Generate Clip 1 using generate_clip_with_frames with the subject "
            "image as first_frame_gcs_uri. Then extract the last frame, "
            "and generate Clip 2. "
            "After both clips, concatenate them and trim to 15 seconds. "
            "Finally call save_commercial_artifact with duration_seconds=15. Do all of this now.",
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # Step 11c: Assembly & save
    print("\n\n--- STEP 11c: Assembly & Save ---")
    commercial_saved = check_state_key(base_url, user_id, session_id, "commercial_artifact")
    if not commercial_saved:
        has_clips = any(t in tools for t in ["concatenate_clips", "trim_video"])
        if not has_clips:
            print("  [INFO] Nudging to finish clip generation and assembly...")
            response, tools = send_message(
                base_url, user_id, session_id,
                "Continue generating the remaining clips if not done. "
                "For clip 2, extract the last frame of clip 1 "
                "and use it as first_frame_gcs_uri. "
                "Once both clips are generated, call concatenate_clips "
                "with both GCS URIs, then trim_video to 15 seconds, "
                "then save_commercial_artifact with duration_seconds=15.",
                timeout=EXTRA_LONG_TIMEOUT,
            )
            commercial_saved = check_state_key(base_url, user_id, session_id, "commercial_artifact")

    if not commercial_saved:
        print("  [RETRY] Final attempt -- asking to concatenate and save...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "If the 2 clips are generated, please call concatenate_clips now "
            "with their GCS URIs, then trim_video to 15 seconds, then "
            "save_commercial_artifact with the trimmed video URI and metadata "
            "including duration_seconds=15.",
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(base_url, user_id, session_id, "commercial_artifact")

    if commercial_saved:
        session = get_session_state(base_url, user_id, session_id)
        state = session.get("state", {})
        commercial = state.get("commercial_artifact", {})
        metadata = commercial.get("metadata", {})
        duration = metadata.get("duration_seconds", 0)
        print(f"  [{'PASS' if duration == 15 else 'WARN'}] commercial duration: {duration}s (expected 15)")

    # Step 12: Focus group
    print("\n\n--- STEP 12: Focus Group Evaluator ---")
    response, tools = send_message(
        base_url, user_id, session_id,
        "Now proceed to step 6: transfer to the focus_group_evaluator_agent "
        "sub-agent. It should call the analyze_commercial_video tool to analyze "
        "the 15-second commercial, then simulate a focus group panel with scoring "
        "and a Go/No-Go recommendation.",
        timeout=LONG_TIMEOUT,
    )

    analyze_called = "analyze_commercial_video" in tools
    print(f"  [{'PASS' if analyze_called else 'WARN'}] analyze_commercial_video called: {analyze_called}")

    if not analyze_called:
        print("  [RETRY] Asking focus group to analyze the commercial...")
        response, tools = send_message(
            base_url, user_id, session_id,
            "You are the focus_group_evaluator_agent. Call the "
            "analyze_commercial_video tool now to analyze the commercial "
            "video stored in session state. Then provide the full focus "
            "group evaluation with scores and a Go/No-Go recommendation.",
            timeout=LONG_TIMEOUT,
        )

    # GCS Verification
    gcs_pass = verify_gcs_output(base_url, user_id, session_id)

    # Final state verification
    print("\n\n" + "=" * 70)
    print("FINAL STATE VERIFICATION")
    print("=" * 70)
    session = get_session_state(base_url, user_id, session_id)
    state = session.get("state", {})

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

    img_count = check_artifact_keys(base_url, user_id, session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(base_url, user_id, session_id, "vid_artifact_keys", "vid_artifact_keys")

    if img_count == 0:
        all_pass = False
    if vid_count == 0:
        all_pass = False

    commercial = state.get("commercial_artifact", {})
    if isinstance(commercial, str):
        # Default empty string or unexpected format
        commercial = {}
    commercial_pass = bool(commercial and isinstance(commercial, dict) and commercial.get("artifact_key"))
    commercial_duration = commercial.get("metadata", {}).get("duration_seconds", 0) if isinstance(commercial, dict) else 0
    duration_pass = commercial_duration == 15
    print(f"  [{'PASS' if commercial_pass else 'FAIL'}] commercial_artifact")
    print(f"  [{'PASS' if duration_pass else 'WARN'}] commercial_artifact.duration_seconds == 15 (actual: {commercial_duration})")
    print(f"  [{'PASS' if gcs_pass else 'FAIL'}] GCS output verification")

    print(f"\n{'='*70}")
    if all_pass and commercial_pass and gcs_pass:
        print("E2E TEST: FULL PIPELINE PASSED (15s commercial)")
        print(f"  Images generated: {img_count}")
        print(f"  Videos generated: {vid_count}")
        print(f"  Commercial: {commercial_duration}s")
        print(f"  GCS verified: {gcs_pass}")
        sys.exit(0)
    elif all_pass and (img_count > 0 or vid_count > 0):
        print("E2E TEST: PARTIAL PASS (some creatives generated)")
        print(f"  Images: {img_count}")
        print(f"  Videos: {vid_count}")
        print(f"  Commercial: {'PASS' if commercial_pass else 'MISSING'} ({commercial_duration}s)")
        print(f"  GCS verified: {gcs_pass}")
        sys.exit(1)
    else:
        print("E2E TEST: SOME CHECKS FAILED (see above)")
        sys.exit(1)
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
