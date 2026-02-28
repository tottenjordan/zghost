"""
E2E test for trends_and_insights_agent on Agent Engine (Vertex AI).
Tests: Google Pixel 9 / Tech-savvy millennials / 12-second commercial

Focus: Full pipeline with auto trend selection, research, ad creative,
visual generation, AV editing studio (12s commercial with 2 clips).

Target: 12-second commercial with 2 clips (~6s each).

Usage:
  python tests/ae_e2e_pixel9_12s_test.py
"""

import json
import os
import sys
import time
import uuid

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Configuration
PROJECT_ID = "wortz-project-352116"
PROJECT_NUMBER = "679926387543"
LOCATION = "us-central1"
AGENT_ENGINE_ID = "225649472833585152"
RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
USER_ID = f"test-user-{uuid.uuid4().hex[:8]}"

# Timeouts in seconds
SHORT_TIMEOUT = 180
MEDIUM_TIMEOUT = 360
LONG_TIMEOUT = 600
EXTRA_LONG_TIMEOUT = 900


def setup_client():
    """Initialize Vertex AI client and get the agent engines API."""
    import vertexai

    print(f"[CONFIG] Project: {PROJECT_ID}")
    print(f"[CONFIG] Location: {LOCATION}")
    print(f"[CONFIG] Resource: {RESOURCE_NAME}")
    print(f"[CONFIG] User: {USER_ID}")

    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    ae = client.agent_engines

    # Verify the agent exists
    agent = ae.get(name=RESOURCE_NAME)
    print(f"[CONFIG] Agent engine found: {agent.api_resource.display_name}")
    print(f"[CONFIG] Created: {agent.api_resource.create_time}")

    return client, ae


def create_session(ae):
    """Create a new session on Agent Engine."""
    session_op = ae.sessions.create(name=RESOURCE_NAME, user_id=USER_ID)
    session = session_op.response
    session_name = session.name
    session_id = session_name.split("/sessions/")[-1]
    print(f"[SESSION] Created session: {session_id}")
    print(f"[SESSION] Full name: {session_name}")
    return session_name, session_id


def send_message(ae, session_id, message, timeout=SHORT_TIMEOUT):
    """Send a message via stream_query. Returns (full_text, tool_calls, transfers)."""
    from vertexai._genai.types.common import QueryAgentEngineConfig

    print(f"\n{'='*80}")
    print(f"[USER] {message[:400]}{'...' if len(message) > 400 else ''}")
    print(f"{'='*80}")

    config = QueryAgentEngineConfig(
        class_method="stream_query",
        input={
            "user_id": USER_ID,
            "session_id": session_id,
            "message": message,
        },
    )

    start = time.time()
    all_text = []
    tool_calls = []
    transfers = []
    event_count = 0

    try:
        for event in ae._stream_query(name=RESOURCE_NAME, config=config):
            event_count += 1
            elapsed = time.time() - start

            # Parse the body JSON
            body_str = event.body if hasattr(event, "body") else ""
            if not body_str:
                continue

            try:
                body = json.loads(body_str)
            except (json.JSONDecodeError, TypeError):
                print(f"  [EVENT {event_count}] ({elapsed:.1f}s) <unparseable body>")
                continue

            # Extract author and invocation info
            author = body.get("author", "")
            inv_id = body.get("invocation_id", "")[:20] if body.get("invocation_id") else ""

            # Extract text from content.parts
            content = body.get("content", {})
            parts = content.get("parts", [])
            event_text = []
            event_tool_calls = []
            event_transfers = []

            for part in parts:
                if isinstance(part, dict):
                    if "text" in part:
                        event_text.append(part["text"])
                    if "function_call" in part:
                        fc = part["function_call"]
                        fc_name = fc.get("name", "?")
                        fc_args = fc.get("args", {})
                        event_tool_calls.append(fc_name)
                        tool_calls.append(fc_name)
                        args_str = str(fc_args)
                        if len(args_str) > 150:
                            args_str = args_str[:150] + "..."
                        print(f"  [TOOL CALL] ({elapsed:.1f}s) {author} -> {fc_name}({args_str})")
                    if "function_response" in part:
                        fr = part["function_response"]
                        fr_name = fr.get("name", "?")
                        fr_response = fr.get("response", {})
                        resp_str = str(fr_response)
                        if len(resp_str) > 200:
                            resp_str = resp_str[:200] + "..."
                        print(f"  [TOOL RESP] ({elapsed:.1f}s) {author} <- {fr_name}: {resp_str}")

            # Extract transfers from actions
            actions = body.get("actions", {})
            if isinstance(actions, dict):
                transfer_to = actions.get("transfer_to_agent")
                if transfer_to:
                    transfers.append(transfer_to)
                    event_transfers.append(transfer_to)
                    print(f"  [TRANSFER] ({elapsed:.1f}s) {author} -> {transfer_to}")

                # Log state delta keys
                state_delta = actions.get("state_delta", {})
                if state_delta and not state_delta.get("_state_init"):
                    delta_keys = [k for k in state_delta.keys() if k != "_state_init"]
                    if delta_keys:
                        print(f"  [STATE DELTA] ({elapsed:.1f}s) {author}: {', '.join(delta_keys)}")

            # Collect text
            if event_text:
                all_text.extend(event_text)
                combined = " ".join(event_text)
                if len(combined) > 300:
                    combined = combined[:300] + "..."
                print(f"  [TEXT] ({elapsed:.1f}s) {author}: {combined}")

            # If no text and no tool call and no transfer -- print a summary line
            if not event_text and not event_tool_calls and not event_transfers:
                # Just print a dot for state-only events
                body_preview = body_str[:100] if len(body_str) < 100 else body_str[:100] + "..."
                # Only print for non-trivial events
                if "content" not in body and "actions" in body:
                    pass  # Skip pure state events silently
                elif "finish_reason" in body:
                    print(f"  [FINISH] ({elapsed:.1f}s) {author} finish_reason={body.get('finish_reason')}")

            # Timeout check
            if elapsed > timeout:
                print(f"  [TIMEOUT] Exceeded {timeout}s, stopping stream")
                break

    except Exception as e:
        elapsed = time.time() - start
        print(f"[ERROR] ({elapsed:.1f}s) {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None, tool_calls, transfers

    elapsed = time.time() - start
    full_response = "\n".join(all_text) if all_text else ""

    print(f"\n[SUMMARY] ({elapsed:.1f}s, {event_count} events, {len(tool_calls)} tool calls, {len(transfers)} transfers)")
    if full_response:
        display = full_response[:2000] + "..." if len(full_response) > 2000 else full_response
        print(f"[FINAL RESPONSE]\n{display}")

    return full_response, tool_calls, transfers


def get_session_state(ae, session_id):
    """Get current session state from Agent Engine."""
    try:
        session_name = f"{RESOURCE_NAME}/sessions/{session_id}"
        session = ae.sessions.get(name=session_name)
        if hasattr(session, "session_state") and session.session_state:
            return session.session_state
        return {}
    except Exception as e:
        print(f"  [WARN] Could not get session state: {e}")
        return {}


def check_state_key(ae, session_id, key):
    """Check if a state key has been set."""
    state = get_session_state(ae, session_id)
    value = state.get(key)
    if value and value != "" and value != {} and value != []:
        print(f"  [STATE] '{key}' is SET")
        val_str = str(value)
        if len(val_str) > 200:
            val_str = val_str[:200] + "..."
        print(f"    Preview: {val_str}")
        return True
    else:
        print(f"  [STATE] '{key}' is NOT set or empty")
        return False


def check_artifact_keys(ae, session_id, key, inner_key):
    """Check that an artifact key dict has at least 1 entry."""
    state = get_session_state(ae, session_id)
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


def print_all_state_keys(ae, session_id):
    """Print all session state keys for debugging."""
    state = get_session_state(ae, session_id)
    print(f"\n  [ALL STATE KEYS] ({len(state)} keys):")
    for key in sorted(state.keys()):
        val = state[key]
        val_str = str(val)
        if len(val_str) > 120:
            val_str = val_str[:120] + "..."
        print(f"    {key}: {val_str}")


def main():
    print("=" * 80)
    print("Agent Engine E2E Test: Google Pixel 9 / Tech-Savvy Millennials")
    print("Goal: 12-second commercial with 2 clips (~6s each)")
    print(f"Agent Engine ID: {AGENT_ENGINE_ID}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Setup
    client, ae = setup_client()
    session_name, session_id = create_session(ae)

    # ===================================================================
    # Step 1: Say hello
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 1: Greeting")
    print("#" * 80)
    response, tools, transfers = send_message(ae, session_id, "hello", timeout=SHORT_TIMEOUT)
    if response is None:
        print("[FATAL] No response to greeting")
        sys.exit(1)

    if "KeyError" in (response or "") or "Context variable not found" in (response or ""):
        print("[FAIL] KeyError detected in greeting response!")
        sys.exit(1)
    print("[PASS] Greeting successful")

    # ===================================================================
    # Step 2: Provide campaign metadata
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 2: Campaign Metadata")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        (
            "Brand: Google, Product: Pixel 9, "
            "Audience: Tech-savvy millennials, "
            "Key Selling Points: AI-powered camera with Magic Eraser, "
            "Tensor G4 chip, 7 years of updates, best photo quality"
        ),
        timeout=SHORT_TIMEOUT,
    )

    time.sleep(2)
    check_state_key(ae, session_id, "brand")
    check_state_key(ae, session_id, "target_product")
    check_state_key(ae, session_id, "target_audience")
    check_state_key(ae, session_id, "key_selling_points")

    # ===================================================================
    # Step 3: Auto-select trends
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 3: Auto-Select Trends")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        (
            "Auto-select the best trends for this campaign. "
            "Pick brand-safe Google Search and YouTube trends "
            "relevant to Google Pixel 9 for tech-savvy millennials."
        ),
        timeout=MEDIUM_TIMEOUT,
    )

    search_saved = check_state_key(ae, session_id, "target_search_trends")
    yt_saved = check_state_key(ae, session_id, "target_yt_trends")

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
        response, tools, transfers = send_message(ae, session_id, retry_msg, timeout=MEDIUM_TIMEOUT)
        search_saved = check_state_key(ae, session_id, "target_search_trends")
        yt_saved = check_state_key(ae, session_id, "target_yt_trends")

    # ===================================================================
    # Step 4: Confirm and proceed to research
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 4: Confirm Selections -> Research")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        "Looks great, proceed with research.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(ae, session_id, "combined_final_cited_report"):
        print("  Waiting for research to complete...")
        response, tools, transfers = send_message(
            ae, session_id,
            "Please continue with the research pipeline and generate the full report.",
            timeout=LONG_TIMEOUT,
        )
        check_state_key(ae, session_id, "combined_final_cited_report")

    # ===================================================================
    # Step 5: Proceed to ad generation
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 5: Report -> Ad Generation")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        "Report looks good, proceed to ad generation.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(ae, session_id, "ad_copy_critique"):
        response, tools, transfers = send_message(
            ae, session_id,
            "Please generate the ad copies now.",
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 6: Select ad copies
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 6: Select Ad Copies")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        (
            "These ad copies look great. I want to select ad copies 1, 2, and 3. "
            "Please use the save_select_ad_copy tool to save each of these three "
            "ad copies one at a time."
        ),
        timeout=MEDIUM_TIMEOUT,
    )

    if not check_state_key(ae, session_id, "final_select_ad_copies"):
        print("  [WARN] Retrying ad copy selection...")
        response, tools, transfers = send_message(
            ae, session_id,
            (
                "Please save ad copies 1, 2, and 3 using the save_select_ad_copy tool. "
                "Call save_select_ad_copy once for each ad copy."
            ),
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(ae, session_id, "final_select_ad_copies")

    # ===================================================================
    # Step 7: Visual generation pipeline
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 7: Visual Generation Pipeline")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        (
            "Great, the ad copies are saved. Now please proceed with step 4 of your "
            "workflow: call the visual_generation_pipeline tool to generate visual "
            "concepts for the selected ad copies."
        ),
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(ae, session_id, "final_visual_concepts"):
        response, tools, transfers = send_message(
            ae, session_id,
            "Please continue with the visual concept generation.",
            timeout=LONG_TIMEOUT,
        )

    # ===================================================================
    # Step 8: Select visual concepts
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 8: Select Visual Concepts")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        (
            "I want to select visual concepts for generation. "
            "Please select and save 2 visual concepts using the save_select_visual_concept tool:\n"
            "- Select the first image-type concept from the list and save it with type 'image'\n"
            "- Select the first video-type concept from the list and save it with type 'video'\n"
            "Call save_select_visual_concept once for each concept, chaining the calls."
        ),
        timeout=MEDIUM_TIMEOUT,
    )

    if not check_state_key(ae, session_id, "final_select_vis_concepts"):
        print("  [WARN] Retrying visual concept selection...")
        response, tools, transfers = send_message(
            ae, session_id,
            (
                "Please use the save_select_visual_concept tool to save at least "
                "2 visual concepts: one with type 'image' and one with type 'video'. "
                "Call save_select_visual_concept once per concept."
            ),
            timeout=MEDIUM_TIMEOUT,
        )
        check_state_key(ae, session_id, "final_select_vis_concepts")

    # ===================================================================
    # Step 9: Generate visuals
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 9: Generate Visuals (Imagen + Veo)")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
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

    img_count = check_artifact_keys(ae, session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(ae, session_id, "vid_artifact_keys", "vid_artifact_keys")

    if img_count == 0 and vid_count == 0:
        print("\n  [RETRY] No artifacts saved, retrying...")
        response, tools, transfers = send_message(
            ae, session_id,
            (
                "The visual generation step did not produce any artifacts. "
                "Please call the visual_generator tool now to generate the creatives. "
                "Then call save_img_artifact_key for each image and "
                "save_vid_artifact_key for each video that was generated."
            ),
            timeout=LONG_TIMEOUT,
        )
        img_count = check_artifact_keys(ae, session_id, "img_artifact_keys", "img_artifact_keys")
        vid_count = check_artifact_keys(ae, session_id, "vid_artifact_keys", "vid_artifact_keys")

    # ===================================================================
    # Step 10: Save creatives report
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 10: Save Creatives Report")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        (
            "I'm satisfied with the generated creatives. "
            "Please call the save_creatives_and_research_report tool now to build "
            "the final PDF report that includes the web research and ad creatives."
        ),
        timeout=LONG_TIMEOUT,
    )

    # ===================================================================
    # Step 11: Transfer to AV Editing Studio for 12s commercial
    # ===================================================================
    print("\n\n" + "#" * 80)
    print("# STEP 11: AV Editing Studio (12-SECOND Commercial)")
    print("#" * 80)
    response, tools, transfers = send_message(
        ae, session_id,
        (
            "Now transfer to the av_editing_studio_agent to create a SHORT 12-second "
            "commercial video (NOT 30 seconds). The commercial should connect the selected "
            "trends to the Google Pixel 9 campaign for tech-savvy millennials.\n\n"
            "IMPORTANT REQUIREMENTS FOR THIS 12-SECOND FORMAT:\n"
            "- Generate ONLY 2 VIDEO CLIPS (not 4)\n"
            "- Each clip approximately 6 seconds\n"
            "- Final trimmed duration: exactly 12 seconds\n"
            "- 2-scene narrative:\n"
            "  * Scene 1 (Hook + Product Connection): Open with a moment that captures "
            "the audience's attention by referencing the trending topic, then naturally "
            "introduce the Pixel 9\n"
            "  * Scene 2 (Demo + CTA): Show the Pixel 9's AI camera features in action "
            "and end with a compelling call-to-action\n\n"
            "WORKFLOW:\n"
            "1. Plan a 2-scene storyboard with CHARACTER SHEET and PRODUCT SHEET\n"
            "2. Generate subject reference images (at least 2 for the character)\n"
            "3. Generate Clip 1 with first-frame from reference image\n"
            "4. Extract last frame from Clip 1, use as first frame for Clip 2\n"
            "5. Concatenate the 2 clips\n"
            "6. Trim to exactly 12 seconds\n"
            "7. Save the commercial artifact with duration_seconds=12 and total_clips=2\n\n"
            "Start now with the storyboard planning."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    commercial_saved = check_state_key(ae, session_id, "commercial_artifact")
    if not commercial_saved:
        print("  [RETRY] Commercial artifact not saved, nudging the agent...")
        response, tools, transfers = send_message(
            ae, session_id,
            (
                "Please continue with the 12-second commercial production. "
                "If the storyboard is planned, proceed to generate the subject reference images, "
                "then generate the 2 clips, concatenate them, trim to 12 seconds, "
                "and save the commercial artifact. Remember: only 2 clips, 12 seconds total."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(ae, session_id, "commercial_artifact")

    if not commercial_saved:
        print("  [RETRY 2] Still no commercial artifact, sending final nudge...")
        response, tools, transfers = send_message(
            ae, session_id,
            (
                "Please complete the remaining steps for the 12-second commercial now:\n"
                "1. If clips are generated, call concatenate_clips with the clip GCS URIs\n"
                "2. Call trim_video with target_duration_seconds=12\n"
                "3. Call save_commercial_artifact with the final video GCS URI and "
                "metadata (duration_seconds=12, total_clips=2)\n"
                "Do these steps now."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )
        commercial_saved = check_state_key(ae, session_id, "commercial_artifact")

    # ===================================================================
    # Final State Verification
    # ===================================================================
    print("\n\n" + "=" * 80)
    print("FINAL STATE VERIFICATION")
    print("=" * 80)

    print_all_state_keys(ae, session_id)

    state = get_session_state(ae, session_id)

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

    img_count = check_artifact_keys(ae, session_id, "img_artifact_keys", "img_artifact_keys")
    vid_count = check_artifact_keys(ae, session_id, "vid_artifact_keys", "vid_artifact_keys")

    img_pass = img_count > 0
    vid_pass = vid_count > 0

    if not img_pass:
        all_pass = False
    if not vid_pass:
        all_pass = False

    commercial = state.get("commercial_artifact", {})
    commercial_pass = bool(commercial and isinstance(commercial, dict) and commercial.get("artifact_key"))
    commercial_duration = 0
    commercial_gcs_uri = ""
    if isinstance(commercial, dict):
        metadata = commercial.get("metadata", {})
        if isinstance(metadata, dict):
            commercial_duration = metadata.get("duration_seconds", 0)
        commercial_gcs_uri = commercial.get("gcs_uri", "") or commercial.get("artifact_key", "")

    duration_pass = commercial_duration == 12
    print(f"  [{'PASS' if commercial_pass else 'FAIL'}] commercial_artifact exists")
    print(f"  [{'PASS' if duration_pass else 'WARN'}] commercial_artifact.duration_seconds == 12 (actual: {commercial_duration})")
    if commercial_gcs_uri:
        print(f"  [INFO] Commercial GCS URI: {commercial_gcs_uri}")

    # Summary
    print(f"\n{'='*80}")
    if all_pass and commercial_pass:
        print("AGENT ENGINE E2E TEST: FULL PIPELINE PASSED")
        print(f"  Images generated: {img_count}")
        print(f"  Videos generated: {vid_count}")
        print(f"  Commercial duration: {commercial_duration}s (target: 12s)")
        if commercial_gcs_uri:
            print(f"  Commercial URI: {commercial_gcs_uri}")
    elif all_pass and (img_pass or vid_pass):
        print("AGENT ENGINE E2E TEST: PARTIAL PASS (some creatives generated)")
        print(f"  Images: {img_count} ({'PASS' if img_pass else 'MISSING'})")
        print(f"  Videos: {vid_count} ({'PASS' if vid_pass else 'MISSING'})")
        print(f"  Commercial: {'PASS' if commercial_pass else 'MISSING'} ({commercial_duration}s)")
    else:
        print("AGENT ENGINE E2E TEST: SOME CHECKS FAILED (see above)")
    print(f"{'='*80}")

    return commercial_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
