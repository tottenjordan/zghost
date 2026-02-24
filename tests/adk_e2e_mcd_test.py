"""
E2E test for trends_and_insights_agent via ADK web API.
Tests: McDonald's / McRib and Shamrock Shake / Senior Citizens / It's back forever!

Focus: Full pipeline with auto trend selection, research, ad creative,
visual generation, AV editing studio (30s commercial), focus group evaluation,
and iteration loop (AV studio <-> focus group, max 3 iterations).

Usage:
  Terminal 1: poetry run adk web trends_and_insights_agent
  Terminal 2: python tests/adk_e2e_mcd_test.py
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
EXTRA_LONG_TIMEOUT = 900

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
    "save_focus_group_evaluation",
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


def main():
    print("=" * 70)
    print("ADK E2E Test: McDonald's / McRib and Shamrock Shake / Senior Citizens")
    print("Focus: Full pipeline + Focus Group iteration loop (max 3)")
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
            "Audience: Senior Citizens, "
            "Key Selling Points: McRib and Shamrock Shake is back forever!"
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
    print("\n\n--- STEP 11a: Transfer to AV Editing Studio ---")
    response, tools = send_message(
        session_id,
        (
            "Now proceed to step 5: transfer to the av_editing_studio_agent sub-agent. "
            "The AV studio should produce a 30-second commercial. "
            "Start by planning the 4-scene storyboard for McRib and Shamrock Shake "
            "targeting Senior Citizens, connecting the selected trends to the product. "
            "Then generate subject reference images with generate_subject_image."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    # Check if subject images were generated (Step 2 of AV pipeline)
    has_subject_tools = any(t in tools for t in ["generate_subject_image", "transfer_to_agent"])
    if not has_subject_tools:
        print("  [INFO] Agent may have presented storyboard; nudging to generate subjects...")
        response, tools = send_message(
            session_id,
            (
                "The storyboard looks good. Now execute Step 2: "
                "call generate_subject_image for the primary character and product. "
                "Then proceed to Step 3: generate all 4 clips using "
                "generate_clip_with_frames with frame chaining."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # Step 11b: Check if clips are being generated
    print("\n\n--- STEP 11b: Clip Generation ---")
    has_clip_tools = any(t in tools for t in [
        "generate_clip_with_frames", "extract_frame_from_clip",
        "concatenate_clips", "trim_video", "save_commercial_artifact",
    ])
    if not has_clip_tools:
        print("  [INFO] Clips not started yet, sending explicit instruction...")
        response, tools = send_message(
            session_id,
            (
                "Now execute Step 3 of the AV studio workflow: "
                "Generate Clip 1 using generate_clip_with_frames with the subject "
                "image as first_frame_gcs_uri. Then extract the last frame, "
                "generate Clip 2, and repeat for Clips 3 and 4. "
                "After all 4 clips, concatenate them and trim to 30 seconds. "
                "Finally call save_commercial_artifact. Do all of this now."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # Step 11c: Check for concat/trim/save if clips were generated
    print("\n\n--- STEP 11c: Assembly & Save ---")
    commercial_saved = check_state_key(session_id, "commercial_artifact")
    if not commercial_saved:
        # Check if any clips exist by looking for tool calls
        has_clips = any(t in tools for t in ["concatenate_clips", "trim_video"])
        if not has_clips:
            print("  [INFO] Nudging to finish clip generation and assembly...")
            response, tools = send_message(
                session_id,
                (
                    "Continue generating the remaining clips if not done. "
                    "For each clip, extract the last frame of the previous clip "
                    "and use it as first_frame_gcs_uri for the next. "
                    "Once all 4 clips are generated, call concatenate_clips "
                    "with all 4 GCS URIs, then trim_video to 30 seconds, "
                    "then save_commercial_artifact with full metadata."
                ),
                timeout=EXTRA_LONG_TIMEOUT,
            )
            commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        print("  [RETRY] Final attempt -- asking to concatenate and save...")
        response, tools = send_message(
            session_id,
            (
                "If the 4 clips are generated, please call concatenate_clips now "
                "with their GCS URIs, then trim_video to 30 seconds, then "
                "save_commercial_artifact with the trimmed video URI and metadata "
                "including duration_seconds=30."
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
    # Step 12: Focus Group Evaluation with Iteration Loop
    # ===================================================================
    print("\n\n--- STEP 12: Focus Group Evaluation (Iteration Loop) ---")

    focus_group_prompt = (
        "Now proceed to step 6: transfer to the focus_group_evaluator_agent "
        "sub-agent. It should call the analyze_commercial_video tool to analyze "
        "the 30-second commercial, then simulate a focus group panel with scoring "
        "and a Go/No-Go recommendation. After the evaluation, it MUST call "
        "save_focus_group_evaluation to save the results to session state."
    )

    response, tools = send_message(session_id, focus_group_prompt, timeout=LONG_TIMEOUT)

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
                "group evaluation with scores and a Go/No-Go recommendation. "
                "Finally, call save_focus_group_evaluation to save results."
            ),
            timeout=LONG_TIMEOUT,
        )

    # Check if save_focus_group_evaluation was called
    save_fg_called = "save_focus_group_evaluation" in tools
    if not save_fg_called:
        print("  [RETRY] Asking focus group to save evaluation results...")
        response, tools = send_message(
            session_id,
            (
                "The focus group evaluation is complete but the results were not "
                "saved to session state. Please call save_focus_group_evaluation "
                "now with the overall_score, recommendation (GO or NO-GO), "
                "top_strengths, areas_for_improvement, and iteration_number=1."
            ),
            timeout=MEDIUM_TIMEOUT,
        )

    # Iteration loop: check GO/NO-GO and iterate if needed
    for iteration in range(1, 4):
        print(f"\n  --- Iteration {iteration}: Checking GO/NO-GO ---")
        session = get_session_state(session_id)
        state = session.get("state", {})
        fg_eval = state.get("focus_group_evaluation", {})

        if not fg_eval:
            print(f"  [WARN] focus_group_evaluation not in session state at iteration {iteration}")
            break

        recommendation = fg_eval.get("recommendation", "")
        overall_score = fg_eval.get("overall_score", 0)
        iter_num = fg_eval.get("iteration_number", iteration)
        print(f"  [INFO] Recommendation: {recommendation}, Score: {overall_score}, Iteration: {iter_num}")

        if recommendation == "GO":
            print(f"  [PASS] Focus group approved on iteration {iteration}")
            break

        if iteration < 3:
            areas = fg_eval.get("areas_for_improvement", [])
            areas_text = "; ".join(areas) if areas else "general quality improvements"
            print(f"  [INFO] NO-GO -- sending back to AV studio for revision (areas: {areas_text})")

            revision_prompt = (
                f"The focus group gave a NO-GO recommendation (score: {overall_score}/10). "
                f"The areas for improvement are: {areas_text}. "
                f"Transfer back to av_editing_studio_agent to revise the commercial. "
                f"The AV studio should regenerate the weakest scenes addressing this "
                f"feedback while keeping strong elements. After revision, transfer to "
                f"focus_group_evaluator_agent for re-evaluation."
            )
            response, tools = send_message(
                session_id, revision_prompt, timeout=EXTRA_LONG_TIMEOUT
            )

            # Check if commercial was re-saved
            check_state_key(session_id, "commercial_artifact")

            # Re-evaluate with focus group
            if "save_focus_group_evaluation" not in tools:
                re_eval_prompt = (
                    "The commercial has been revised. Now transfer to "
                    "focus_group_evaluator_agent to re-evaluate the revised commercial. "
                    "The focus group must call analyze_commercial_video and then "
                    "save_focus_group_evaluation with the updated scores."
                )
                response, tools = send_message(
                    session_id, re_eval_prompt, timeout=LONG_TIMEOUT
                )
        else:
            print(f"  [INFO] NO-GO on iteration 3 -- accepting as best-effort")

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

    # Focus group evaluation check
    fg_eval = state.get("focus_group_evaluation", {})
    fg_pass = bool(fg_eval and fg_eval.get("recommendation"))
    fg_recommendation = fg_eval.get("recommendation", "N/A")
    fg_score = fg_eval.get("overall_score", 0)
    fg_iteration = fg_eval.get("iteration_number", 0)
    print(f"  [{'PASS' if fg_pass else 'FAIL'}] focus_group_evaluation")
    print(f"  [INFO] Focus group: {fg_recommendation} (score: {fg_score}, iteration: {fg_iteration})")

    print(f"\n  [{'PASS' if gcs_pass else 'FAIL'}] GCS output verification")

    # Summary
    print(f"\n{'='*70}")
    if all_pass and img_pass and vid_pass and commercial_pass and fg_pass and gcs_pass:
        print("E2E TEST: FULL PIPELINE PASSED")
        print(f"  Images generated: {img_count}")
        print(f"  Videos generated: {vid_count}")
        print(f"  Commercial: {commercial_duration}s")
        print(f"  Focus group: {fg_recommendation} (score: {fg_score}, iterations: {fg_iteration})")
        print(f"  GCS verified: {gcs_pass}")
    elif all_pass and (img_pass or vid_pass):
        print("E2E TEST: PARTIAL PASS (some creatives generated)")
        print(f"  Images: {img_count} ({'PASS' if img_pass else 'MISSING'})")
        print(f"  Videos: {vid_count} ({'PASS' if vid_pass else 'MISSING'})")
        print(f"  Commercial: {'PASS' if commercial_pass else 'MISSING'} ({commercial_duration}s)")
        print(f"  Focus group: {'PASS' if fg_pass else 'MISSING'} ({fg_recommendation})")
        print(f"  GCS verified: {gcs_pass}")
    else:
        print("E2E TEST: SOME CHECKS FAILED (see above)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
