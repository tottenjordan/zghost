"""
E2E test for trends_and_insights_agent on Agent Engine (Vertex AI).
Tests: McDonald's / McRib Shamrock Combos / Gen Z / It's here forever!

Focus: Full pipeline with auto trend selection, research, ad creative,
visual generation, AV editing studio (30s commercial), and focus group evaluation.

Requires:
  - AGENT_ENGINE_RESOURCE_ID env var (from deploy_to_ae.py output)
  - GOOGLE_CLOUD_PROJECT env var
  - Authenticated gcloud credentials

Usage:
  export AGENT_ENGINE_RESOURCE_ID="projects/PROJECT_NUM/locations/us-central1/agents/AGENT_ID"
  python tests/ae_e2e_mcd_test.py
"""

import os
import sys
import time
import uuid

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Configuration
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
RESOURCE_NAME = os.environ.get("AGENT_ENGINE_RESOURCE_ID", "")
USER_ID = f"test-user-{uuid.uuid4().hex[:8]}"

# Timeouts in seconds
SHORT_TIMEOUT = 180
MEDIUM_TIMEOUT = 360
LONG_TIMEOUT = 600
EXTRA_LONG_TIMEOUT = 900


def setup_client():
    """Initialize Vertex AI client and get the remote agent."""
    import vertexai

    if not PROJECT_ID:
        print("[FATAL] GOOGLE_CLOUD_PROJECT env var not set")
        sys.exit(1)
    if not RESOURCE_NAME:
        print("[FATAL] AGENT_ENGINE_RESOURCE_ID env var not set")
        print("  Run deploy_to_ae.py first, then set this env var to the resource name.")
        sys.exit(1)

    print(f"[CONFIG] Project: {PROJECT_ID}")
    print(f"[CONFIG] Location: {LOCATION}")
    print(f"[CONFIG] Resource: {RESOURCE_NAME}")
    print(f"[CONFIG] User: {USER_ID}")

    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    remote_agent = client.agent_engines.get(RESOURCE_NAME)
    return client, remote_agent


def create_session(remote_agent):
    """Create a new session on Agent Engine."""
    session = remote_agent.create_session(user_id=USER_ID)
    print(f"[SESSION] Created session: {session.id}")
    return session


def send_message(remote_agent, session, message, timeout=SHORT_TIMEOUT):
    """Send a message to the remote agent. Returns (full_text, events_list)."""
    print(f"\n{'='*70}")
    print(f"[USER] {message[:200]}{'...' if len(message) > 200 else ''}")
    print(f"{'='*70}")

    start = time.time()
    try:
        response = remote_agent.query(
            input=message,
            session_id=session.id,
            user_id=USER_ID,
        )
        elapsed = time.time() - start
    except Exception as e:
        elapsed = time.time() - start
        print(f"[ERROR] ({elapsed:.1f}s) {e}")
        return None, []

    # Extract text and tool calls from response
    response_texts = []
    tool_calls = []

    # The response structure may vary; handle both dict and object forms
    if hasattr(response, "output"):
        # ADK Agent Engine response
        output = response.output
        if isinstance(output, str):
            response_texts.append(output)
        elif isinstance(output, dict):
            if "text" in output:
                response_texts.append(output["text"])
            if "parts" in output:
                for part in output["parts"]:
                    if isinstance(part, dict) and "text" in part:
                        response_texts.append(part["text"])
    elif isinstance(response, dict):
        if "output" in response:
            output = response["output"]
            if isinstance(output, str):
                response_texts.append(output)
        if "text" in response:
            response_texts.append(response["text"])

    # Try to extract tool calls from events if available
    if hasattr(response, "events"):
        for event in response.events:
            if hasattr(event, "function_call"):
                tool_name = event.function_call.name if hasattr(event.function_call, "name") else str(event.function_call)
                tool_calls.append(tool_name)
                print(f"  [TOOL] {tool_name}")

    full_response = "\n".join(response_texts) if response_texts else str(response)
    display = full_response[:2000] + "..." if len(full_response) > 2000 else full_response
    print(f"\n[AGENT] ({elapsed:.1f}s) {display}")
    if tool_calls:
        print(f"  [TOOLS CALLED] {', '.join(tool_calls)}")
    return full_response, tool_calls


def get_session_state(remote_agent, session):
    """Get current session state from Agent Engine."""
    try:
        updated_session = remote_agent.get_session(
            session_id=session.id,
            user_id=USER_ID,
        )
        if hasattr(updated_session, "state"):
            return updated_session.state or {}
        return {}
    except Exception as e:
        print(f"  [WARN] Could not get session state: {e}")
        return {}


def check_state_key(remote_agent, session, key):
    """Check if a state key has been set."""
    state = get_session_state(remote_agent, session)
    value = state.get(key)
    if value and value != "" and value != {} and value != []:
        print(f"  [STATE] '{key}' is set")
        return True
    else:
        print(f"  [STATE] '{key}' is NOT set or empty")
        return False


def check_artifact_keys(remote_agent, session, key, inner_key):
    """Check that an artifact key dict has at least 1 entry."""
    state = get_session_state(remote_agent, session)
    outer = state.get(key, {})
    items = outer.get(inner_key, []) if isinstance(outer, dict) else []
    count = len(items)
    status = "PASS" if count > 0 else "FAIL"
    print(f"  [{status}] {key} -> {inner_key}: {count} entries")
    if count > 0:
        for i, entry in enumerate(items):
            ak = entry.get("artifact_key", "?") if isinstance(entry, dict) else str(entry)
            print(f"    [{i}] {ak}")
    return count


def main():
    print("=" * 70)
    print("Agent Engine E2E Test: McDonald's / McRib Shamrock Combos / Gen Z")
    print("Focus: Auto trend selection + AV studio + Focus group")
    print("=" * 70)

    # Setup
    client, remote_agent = setup_client()
    session = create_session(remote_agent)

    # ===================================================================
    # Step 1: Say hello
    # ===================================================================
    print("\n\n--- STEP 1: Greeting ---")
    response, tools = send_message(remote_agent, session, "hello", timeout=SHORT_TIMEOUT)
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
        remote_agent, session,
        (
            "Brand: McDonald's, Product: McRib Shamrock Combos, "
            "Audience: Gen Z, Key Selling Points: It's here forever!"
        ),
        timeout=SHORT_TIMEOUT,
    )

    time.sleep(2)
    check_state_key(remote_agent, session, "brand")
    check_state_key(remote_agent, session, "target_product")
    check_state_key(remote_agent, session, "target_audience")
    check_state_key(remote_agent, session, "key_selling_points")

    # ===================================================================
    # Step 3: Auto-select trends
    # ===================================================================
    print("\n\n--- STEP 3: Auto-Select Trends ---")
    response, tools = send_message(
        remote_agent, session,
        (
            "Auto-select the best trends for this campaign. "
            "Pick brand-safe Google Search and YouTube trends "
            "relevant to McDonald's McRib Shamrock Combos for Gen Z."
        ),
        timeout=MEDIUM_TIMEOUT,
    )

    search_saved = check_state_key(remote_agent, session, "target_search_trends")
    yt_saved = check_state_key(remote_agent, session, "target_yt_trends")

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
        response, tools = send_message(remote_agent, session, retry_msg, timeout=MEDIUM_TIMEOUT)
        check_state_key(remote_agent, session, "target_search_trends")
        check_state_key(remote_agent, session, "target_yt_trends")

    # ===================================================================
    # Step 4: Confirm and proceed to research
    # ===================================================================
    print("\n\n--- STEP 4: Confirm Selections -> Research ---")
    response, tools = send_message(
        remote_agent, session,
        "Looks great, proceed with research.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(remote_agent, session, "combined_final_cited_report"):
        print("  Waiting for research to complete...")
        response, tools = send_message(
            remote_agent, session,
            "Please continue with the research pipeline",
            timeout=LONG_TIMEOUT,
        )
        check_state_key(remote_agent, session, "combined_final_cited_report")

    # ===================================================================
    # Step 5: Proceed to ad generation
    # ===================================================================
    print("\n\n--- STEP 5: Report -> Ad Generation ---")
    response, tools = send_message(
        remote_agent, session,
        "Report looks good, proceed to ad generation.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(remote_agent, session, "ad_copy_critique"):
        response, tools = send_message(
            remote_agent, session,
            "Please generate the ad copies",
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 6: Select ad copies
    # ===================================================================
    print("\n\n--- STEP 6: Select Ad Copies ---")
    response, tools = send_message(
        remote_agent, session,
        (
            "These ad copies look great. I want to select ad copies 1, 2, and 3. "
            "Please use the save_select_ad_copy tool to save each of these three "
            "ad copies one at a time."
        ),
        timeout=MEDIUM_TIMEOUT,
    )
    check_state_key(remote_agent, session, "final_select_ad_copies")

    if not check_state_key(remote_agent, session, "final_select_ad_copies"):
        print("  [WARN] Retrying ad copy selection...")
        response, tools = send_message(
            remote_agent, session,
            (
                "Please save ad copies 1, 2, and 3 using the save_select_ad_copy tool. "
                "Call save_select_ad_copy once for each ad copy."
            ),
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(remote_agent, session, "final_select_ad_copies")

    # ===================================================================
    # Step 7: Visual generation pipeline
    # ===================================================================
    print("\n\n--- STEP 7: Visual Generation Pipeline ---")
    response, tools = send_message(
        remote_agent, session,
        (
            "Great, the ad copies are saved. Now please proceed with step 4 of your "
            "workflow: call the visual_generation_pipeline tool to generate visual "
            "concepts for the selected ad copies."
        ),
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(remote_agent, session, "final_visual_concepts"):
        response, tools = send_message(
            remote_agent, session,
            "Please continue with the visual concept generation",
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 8: Select visual concepts
    # ===================================================================
    print("\n\n--- STEP 8: Select Visual Concepts ---")
    response, tools = send_message(
        remote_agent, session,
        (
            "I want to select visual concepts for generation. "
            "Please select and save 2 visual concepts using the save_select_visual_concept tool:\n"
            "- Select the first image-type concept from the list and save it with type 'image'\n"
            "- Select the first video-type concept from the list and save it with type 'video'\n"
            "Call save_select_visual_concept once for each concept, chaining the calls."
        ),
        timeout=MEDIUM_TIMEOUT,
    )
    check_state_key(remote_agent, session, "final_select_vis_concepts")

    if not check_state_key(remote_agent, session, "final_select_vis_concepts"):
        print("  [WARN] Retrying visual concept selection...")
        response, tools = send_message(
            remote_agent, session,
            (
                "Please use the save_select_visual_concept tool to save at least "
                "2 visual concepts: one with type 'image' and one with type 'video'. "
                "Call save_select_visual_concept once per concept."
            ),
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(remote_agent, session, "final_select_vis_concepts")

    # ===================================================================
    # Step 9: Generate visuals
    # ===================================================================
    print("\n\n--- STEP 9: Generate Visuals (Imagen + Veo) ---")
    response, tools = send_message(
        remote_agent, session,
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

    img_count = check_artifact_keys(remote_agent, session, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(remote_agent, session, "vid_artifact_keys", "vid_artifact_keys")

    if img_count == 0 and vid_count == 0:
        print("\n  [RETRY] No artifacts saved, retrying...")
        response, tools = send_message(
            remote_agent, session,
            (
                "The visual generation step did not produce any artifacts. "
                "Please call the visual_generator tool now to generate the creatives. "
                "Then call save_img_artifact_key for each image and "
                "save_vid_artifact_key for each video that was generated."
            ),
            timeout=LONG_TIMEOUT,
        )
        img_count = check_artifact_keys(remote_agent, session, "img_artifact_keys", "img_artifact_keys")
        vid_count = check_artifact_keys(remote_agent, session, "vid_artifact_keys", "vid_artifact_keys")

    # ===================================================================
    # Step 10: Save creatives report
    # ===================================================================
    print("\n\n--- STEP 10: Save Creatives Report ---")
    response, tools = send_message(
        remote_agent, session,
        (
            "I'm satisfied with the generated creatives. "
            "Please call the save_creatives_and_research_report tool now to build "
            "the final PDF report that includes the web research and ad creatives."
        ),
        timeout=LONG_TIMEOUT,
    )

    # ===================================================================
    # Step 11: Transfer to AV Editing Studio for 30s commercial
    # ===================================================================
    print("\n\n--- STEP 11: AV Editing Studio (30s Commercial) ---")
    response, tools = send_message(
        remote_agent, session,
        (
            "Now transfer to the av_editing_studio_agent to create a 30-second "
            "commercial video. The commercial should connect the selected trends "
            "to the McDonald's McRib Shamrock Combos campaign for Gen Z. "
            "Use the full pipeline: generate subject images, create 4 clip scenes "
            "with frame chaining, concatenate, trim to 30 seconds, and save the "
            "commercial artifact."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    commercial_saved = check_state_key(remote_agent, session, "commercial_artifact")
    if not commercial_saved:
        print("  [RETRY] Commercial artifact not saved, retrying...")
        response, tools = send_message(
            remote_agent, session,
            (
                "Please complete the 30-second commercial. If clips are generated, "
                "concatenate them, trim to 30 seconds, and call save_commercial_artifact "
                "with the final video and metadata."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(remote_agent, session, "commercial_artifact")

    if commercial_saved:
        state = get_session_state(remote_agent, session)
        commercial = state.get("commercial_artifact", {})
        metadata = commercial.get("metadata", {})
        duration = metadata.get("duration_seconds", 0)
        print(f"  [{'PASS' if duration == 30 else 'WARN'}] commercial duration: {duration}s (expected 30)")

    # ===================================================================
    # Step 12: Transfer to Focus Group Evaluator
    # ===================================================================
    print("\n\n--- STEP 12: Focus Group Evaluator ---")
    response, tools = send_message(
        remote_agent, session,
        (
            "Now transfer to the focus_group_evaluator_agent to evaluate the "
            "commercial. The focus group should analyze the video using the "
            "analyze_commercial_video tool and provide scoring, panelist reactions, "
            "and a Go/No-Go recommendation."
        ),
        timeout=LONG_TIMEOUT,
    )

    analyze_called = "analyze_commercial_video" in tools
    print(f"  [{'PASS' if analyze_called else 'WARN'}] analyze_commercial_video called: {analyze_called}")

    if not analyze_called:
        print("  [RETRY] Asking focus group to analyze the commercial...")
        response, tools = send_message(
            remote_agent, session,
            (
                "Please use the analyze_commercial_video tool to analyze the "
                "30-second commercial video, then provide the full focus group "
                "evaluation with scores and recommendations."
            ),
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 13: Final State Verification
    # ===================================================================
    print("\n\n" + "=" * 70)
    print("FINAL STATE VERIFICATION")
    print("=" * 70)
    state = get_session_state(remote_agent, session)

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

    img_count = check_artifact_keys(remote_agent, session, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(remote_agent, session, "vid_artifact_keys", "vid_artifact_keys")

    img_pass = img_count > 0
    vid_pass = vid_count > 0

    if not img_pass:
        all_pass = False
    if not vid_pass:
        all_pass = False

    commercial = state.get("commercial_artifact", {})
    commercial_pass = bool(commercial and commercial.get("artifact_key"))
    commercial_duration = commercial.get("metadata", {}).get("duration_seconds", 0) if isinstance(commercial, dict) else 0
    duration_pass = commercial_duration == 30
    print(f"  [{'PASS' if commercial_pass else 'FAIL'}] commercial_artifact")
    print(f"  [{'PASS' if duration_pass else 'WARN'}] commercial_artifact.duration_seconds == 30 (actual: {commercial_duration})")

    # Summary
    print(f"\n{'='*70}")
    if all_pass and img_pass and vid_pass and commercial_pass:
        print("AGENT ENGINE E2E TEST: FULL PIPELINE PASSED")
        print(f"  Images generated: {img_count}")
        print(f"  Videos generated: {vid_count}")
        print(f"  Commercial: {commercial_duration}s")
    elif all_pass and (img_pass or vid_pass):
        print("AGENT ENGINE E2E TEST: PARTIAL PASS (some creatives generated)")
        print(f"  Images: {img_count} ({'PASS' if img_pass else 'MISSING'})")
        print(f"  Videos: {vid_count} ({'PASS' if vid_pass else 'MISSING'})")
        print(f"  Commercial: {'PASS' if commercial_pass else 'MISSING'} ({commercial_duration}s)")
    else:
        print("AGENT ENGINE E2E TEST: SOME CHECKS FAILED (see above)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
