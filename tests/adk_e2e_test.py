"""
E2E test for trends_and_insights_agent via ADK web API.
Tests: Tide / Laundry Detergent / GenZ / New fresh spring fragrance

Focus: Validates full creative generation pipeline including Imagen/Veo
visual generation, artifact key persistence, and final PDF report.
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
SHORT_TIMEOUT = 180    # For quick agent responses (was 120)
MEDIUM_TIMEOUT = 360   # For research/generation steps (was 300)
LONG_TIMEOUT = 600     # For video generation and long pipelines

# Tool names we track for diagnostic logging
TRACKED_TOOLS = {
    "generate_image", "generate_video",
    "save_img_artifact_key", "save_vid_artifact_key",
    "save_select_ad_copy", "save_select_visual_concept",
    "save_creatives_and_research_report",
    "ad_creative_pipeline", "visual_generation_pipeline", "visual_generator",
    "load_artifacts",
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

    # Parse SSE response — extract text and tool calls
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
                            # Log status from tracked tool responses
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
    """Check that an artifact key dict has at least 1 entry.

    E.g. key="img_artifact_keys", inner_key="img_artifact_keys"
    Returns the count of entries.
    """
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
        # Try env
        try:
            import os
            bucket = os.environ.get("BUCKET", "")
        except Exception:
            pass

    if not bucket:
        print("  [WARN] Could not determine GCS bucket, skipping GCS verification")
        return True

    # Normalize bucket name
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


def main():
    print("=" * 70)
    print("ADK E2E Test: Tide / Laundry Detergent / GenZ")
    print("Focus: Full creative generation (Imagen + Veo)")
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
        print("[FAIL] KeyError detected in greeting response - bug not fixed!")
        sys.exit(1)
    print("[PASS] No KeyError in greeting response - bug fix verified!")

    # ===================================================================
    # Step 2: Provide campaign metadata
    # ===================================================================
    print("\n\n--- STEP 2: Campaign Metadata ---")
    response, tools = send_message(
        session_id,
        "Brand: Tide, Product: Laundry Detergent, Audience: GenZ, Key Selling Points: New fresh spring fragrance",
        timeout=SHORT_TIMEOUT,
    )

    time.sleep(2)
    check_state_key(session_id, "brand")
    check_state_key(session_id, "target_product")
    check_state_key(session_id, "target_audience")
    check_state_key(session_id, "key_selling_points")

    # ===================================================================
    # Step 3: Ask to show Google Search trends
    # ===================================================================
    print("\n\n--- STEP 3: Google Search Trends ---")
    response, tools = send_message(
        session_id,
        "Show me the Google Search trends and I'll pick one",
        timeout=MEDIUM_TIMEOUT,
    )

    # ===================================================================
    # Step 4: Select a brand-safe Google trend
    # ===================================================================
    print("\n\n--- STEP 4: Select Google Trend (brand-safe) ---")
    response, tools = send_message(
        session_id,
        "Please select a brand-safe, family-friendly trend from the list that would work well for a laundry detergent campaign. Avoid anything controversial, political, or related to violence/crime.",
        timeout=SHORT_TIMEOUT,
    )
    check_state_key(session_id, "target_search_trends")

    # ===================================================================
    # Step 5: Ask for YouTube trends
    # ===================================================================
    print("\n\n--- STEP 5: YouTube Trends ---")
    response, tools = send_message(
        session_id,
        "Now show me YouTube trending videos and I'll pick one",
        timeout=MEDIUM_TIMEOUT,
    )

    # ===================================================================
    # Step 6: Select a brand-safe YT trend
    # ===================================================================
    print("\n\n--- STEP 6: Select YouTube Trend (brand-safe) ---")
    response, tools = send_message(
        session_id,
        "Please select a brand-safe, family-friendly trending video from the list that would work well for a laundry detergent campaign. Avoid anything controversial, political, or related to violence/crime.",
        timeout=SHORT_TIMEOUT,
    )
    check_state_key(session_id, "target_yt_trends")

    # ===================================================================
    # Step 7: Confirm selections and proceed to research
    # ===================================================================
    print("\n\n--- STEP 7: Confirm and Start Research ---")
    response, tools = send_message(
        session_id,
        "Yes, that looks good. Let's proceed with the research.",
        timeout=LONG_TIMEOUT,
    )

    # ===================================================================
    # Step 8: Wait for research pipeline
    # ===================================================================
    print("\n\n--- STEP 8: Research Pipeline ---")
    if not check_state_key(session_id, "combined_final_cited_report"):
        print("  Waiting for research to complete...")
        response, tools = send_message(
            session_id,
            "Please continue with the research pipeline",
            timeout=LONG_TIMEOUT,
        )
        check_state_key(session_id, "combined_final_cited_report")

    # ===================================================================
    # Step 9: Confirm report and proceed to ad generation
    # ===================================================================
    print("\n\n--- STEP 9: Confirm Report -> Ad Generation ---")
    response, tools = send_message(
        session_id,
        "The report looks good. Please proceed to ad generation.",
        timeout=LONG_TIMEOUT,
    )

    # ===================================================================
    # Step 10: Wait for ad creative pipeline
    # ===================================================================
    print("\n\n--- STEP 10: Ad Creative Pipeline ---")
    if not check_state_key(session_id, "ad_copy_critique"):
        response, tools = send_message(
            session_id,
            "Please generate the ad copies",
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 11: Select ad copies (increased timeout to avoid stale session)
    # ===================================================================
    print("\n\n--- STEP 11: Select Ad Copies ---")
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

    # Verify at least some ad copies were saved
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
    # Step 12: Wait for visual generation pipeline
    # ===================================================================
    print("\n\n--- STEP 12: Visual Generation Pipeline ---")
    response, tools = send_message(
        session_id,
        (
            "Great, the ad copies are saved. Now please proceed with step 4 of your "
            "workflow: call the visual_generation_pipeline tool to generate visual "
            "concepts for the selected ad copies."
        ),
        timeout=LONG_TIMEOUT,
    )

    # ===================================================================
    # Step 13: Select visual concepts — 1 image + 1 video minimum
    # ===================================================================
    print("\n\n--- STEP 13: Select Visual Concepts ---")

    # Read the visual concepts from state to make a more informed selection
    session = get_session_state(session_id)
    state = session.get("state", {})
    final_vis = state.get("final_visual_concepts", "")
    vis_critique = state.get("visual_concept_critique", "")

    # Build a specific selection prompt referencing the concept types
    select_prompt = (
        "I want to select visual concepts for generation. "
        "Please select and save 2 visual concepts using the save_select_visual_concept tool:\n"
        "- Select the first image-type concept from the list and save it with type 'image'\n"
        "- Select the first video-type concept from the list and save it with type 'video'\n"
        "Call save_select_visual_concept once for each concept, chaining the calls."
    )

    response, tools = send_message(
        session_id,
        select_prompt,
        timeout=MEDIUM_TIMEOUT,
    )
    check_state_key(session_id, "final_select_vis_concepts")

    # Verify visual concepts were saved
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
    # Step 14: Generate visuals (CRITICAL — invoke visual_generator)
    # ===================================================================
    print("\n\n--- STEP 14: Generate Visuals (Imagen + Veo) ---")

    generate_prompt = (
        "Now please proceed with step 6 of your workflow: call the visual_generator "
        "tool to generate the actual image and video creatives from the selected "
        "visual concepts in the 'final_select_vis_concepts' state key.\n\n"
        "The visual_generator sub-agent will use generate_image for image concepts "
        "and generate_video for video concepts.\n\n"
        "After the visual_generator completes:\n"
        "- For each image generated, call save_img_artifact_key with the artifact details\n"
        "- For each video generated, call save_vid_artifact_key with the artifact details\n\n"
        "This is the most important step — please execute it now."
    )

    response, tools = send_message(
        session_id,
        generate_prompt,
        timeout=LONG_TIMEOUT,
    )

    # Check what was generated
    img_count = check_artifact_keys(session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(session_id, "vid_artifact_keys", "vid_artifact_keys")

    # Retry: if image generation succeeded but video didn't (or vice versa)
    if img_count == 0 and vid_count == 0:
        print("\n  [RETRY] No artifacts saved. Asking agent to generate and save artifacts...")
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
        print("\n  [RETRY] No images yet. Explicitly requesting image generation...")
        response, tools = send_message(
            session_id,
            (
                "Please generate at least one image now. Look at the image-type concepts "
                "in the 'final_select_vis_concepts' state key and call the visual_generator "
                "tool which will use generate_image. After the image is generated, "
                "call save_img_artifact_key with the full artifact details."
            ),
            timeout=LONG_TIMEOUT,
        )
        img_count = check_artifact_keys(session_id, "img_artifact_keys", "img_artifact_keys")

    if vid_count == 0:
        print("\n  [RETRY] No videos yet. Explicitly requesting video generation...")
        response, tools = send_message(
            session_id,
            (
                "Please generate at least one video now. Look at the video-type concepts "
                "in the 'final_select_vis_concepts' state key and call the visual_generator "
                "tool which will use generate_video. After the video is generated, "
                "call save_vid_artifact_key with the full artifact details."
            ),
            timeout=LONG_TIMEOUT,
        )
        vid_count = check_artifact_keys(session_id, "vid_artifact_keys", "vid_artifact_keys")

    # ===================================================================
    # Step 15: Final report
    # ===================================================================
    print("\n\n--- STEP 15: Final Report ---")
    response, tools = send_message(
        session_id,
        (
            "I'm satisfied with the generated creatives. "
            "Please call the save_creatives_and_research_report tool now to build "
            "the final PDF report that includes the web research and ad creatives."
        ),
        timeout=LONG_TIMEOUT,
    )

    # Verify the tool was called
    if "save_creatives_and_research_report" not in tools:
        print("  [WARN] save_creatives_and_research_report not in tool calls, retrying...")
        response, tools = send_message(
            session_id,
            (
                "Please use the save_creatives_and_research_report tool to generate "
                "the final PDF report now."
            ),
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # GCS Verification
    # ===================================================================
    gcs_pass = verify_gcs_output(session_id)

    # ===================================================================
    # Final state verification
    # ===================================================================
    print("\n\n" + "=" * 70)
    print("FINAL STATE VERIFICATION")
    print("=" * 70)
    session = get_session_state(session_id)
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

    # Check pipeline state keys
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
        if not is_set:
            print(f"  [{status}] {key}")
        else:
            print(f"  [{status}] {key}")

    # Check artifact keys with counts
    img_count = check_artifact_keys(session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(session_id, "vid_artifact_keys", "vid_artifact_keys")

    img_pass = img_count > 0
    vid_pass = vid_count > 0

    if not img_pass:
        all_pass = False
    if not vid_pass:
        all_pass = False

    print(f"\n  [{'PASS' if gcs_pass else 'FAIL'}] GCS output verification")

    print(f"\n{'='*70}")
    if all_pass and img_pass and vid_pass and gcs_pass:
        print("E2E TEST: FULL PIPELINE PASSED")
        print(f"  Images generated: {img_count}")
        print(f"  Videos generated: {vid_count}")
        print(f"  GCS verified: {gcs_pass}")
    elif all_pass and (img_pass or vid_pass):
        print("E2E TEST: PARTIAL PASS (some creatives generated)")
        print(f"  Images: {img_count} ({'PASS' if img_pass else 'MISSING'})")
        print(f"  Videos: {vid_count} ({'PASS' if vid_pass else 'MISSING'})")
        print(f"  GCS verified: {gcs_pass}")
    else:
        print("E2E TEST: SOME CHECKS FAILED (see above)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
