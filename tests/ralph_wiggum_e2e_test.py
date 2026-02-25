"""
Ralph Wiggum E2E Test: Iterative 30s commercial pipeline.

Runs the full ADK flow (trend discovery -> research -> ad creative -> AV studio ->
focus group) and iterates the AV studio + focus group until the focus group gives
a GO recommendation or max iterations are reached.

Campaign: McDonald's / McRib and Shamrock Shake / Senior Citizens
Key features: McRib and Shamrock is back forever

Usage:
  Terminal 1: uv run adk web trends_and_insights_agent
  Terminal 2: python tests/ralph_wiggum_e2e_test.py
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
USER_ID = f"ralph-{uuid.uuid4().hex[:8]}"

# Timeouts in seconds
SHORT_TIMEOUT = 180
MEDIUM_TIMEOUT = 360
LONG_TIMEOUT = 600
EXTRA_LONG_TIMEOUT = 1200

# Ralph Wiggum loop settings
MAX_AV_ITERATIONS = 3

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
    "validate_character_consistency",
    "memorize",
    "get_daily_gtrends", "get_youtube_trends",
    "save_search_trends_to_session_state", "save_yt_trends_to_session_state",
}


# ===================================================================
# Ralph Loop Tracking
# ===================================================================
class RalphLoop:
    """Track ralph-wiggum iterations."""

    def __init__(self, goal, promise, max_iterations):
        self.goal = goal
        self.promise = promise
        self.max_iterations = max_iterations
        self.iterations = []
        self.current = 0

    def start_iteration(self, plan):
        self.current += 1
        self.iterations.append({
            "number": self.current,
            "plan": plan,
            "result": None,
            "status": "IN_PROGRESS",
        })
        print(f"\n{'#'*70}")
        print(f"# RALPH LOOP - Iteration {self.current}/{self.max_iterations}")
        print(f"# Goal: {self.goal}")
        print(f"# Promise: {self.promise}")
        print(f"# Plan: {plan}")
        print(f"{'#'*70}")

    def end_iteration(self, result, status):
        self.iterations[-1]["result"] = result
        self.iterations[-1]["status"] = status
        print(f"\n{'#'*70}")
        print(f"# RALPH LOOP - Iteration {self.current} -> {status}")
        print(f"# Result: {result}")
        print(f"{'#'*70}")

    def is_done(self):
        if not self.iterations:
            return False
        return self.iterations[-1]["status"] == "PASSED"

    def can_continue(self):
        return self.current < self.max_iterations

    def summary(self):
        print(f"\n{'='*70}")
        print("RALPH LOOP SUMMARY")
        print(f"  Goal: {self.goal}")
        print(f"  Promise: {self.promise}")
        print(f"  Total iterations: {self.current}/{self.max_iterations}")
        for it in self.iterations:
            print(f"  Iteration {it['number']}: {it['status']} - {it['result']}")
        final = "PASSED" if self.is_done() else "FAILED"
        print(f"  Final: {final}")
        print(f"{'='*70}")
        return final


# ===================================================================
# Helpers
# ===================================================================

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

    # Parse response -- handle both JSON array and SSE formats
    response_texts = []
    tool_calls = []

    def _process_event(event_data):
        """Extract text and tool calls from a single event dict."""
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
                        gcs = fr_resp.get("gcs_uri", "")
                        extra = ""
                        if artifact:
                            extra = f" artifact_key={artifact}"
                        elif gcs:
                            extra = f" gcs_uri={gcs}"
                        print(f"  [TOOL_RESP] {fr_name}: status={status}{extra}")

    # Try JSON array first (non-streaming response)
    try:
        events = json.loads(resp.text)
        if isinstance(events, list):
            for event_data in events:
                _process_event(event_data)
        elif isinstance(events, dict):
            _process_event(events)
    except (json.JSONDecodeError, TypeError):
        # Fall back to SSE format
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                try:
                    event_data = json.loads(line[5:].strip())
                    _process_event(event_data)
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
    """Check if a state key has been set with meaningful content."""
    session = get_session_state(session_id)
    state = session.get("state", {})
    value = state.get(key)

    # Handle nested dict format like {"target_search_trends": []}
    if isinstance(value, dict) and len(value) == 1:
        inner = list(value.values())[0]
        if isinstance(inner, list) and len(inner) == 0:
            print(f"  [STATE] '{key}' is NOT set or empty (nested empty list)")
            return False

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
    return count


def extract_focus_group_verdict(response):
    """Extract GO or NO-GO from the focus group response.

    Strategy: Find the Go/No-Go Recommendation section and check the
    FINAL verdict there.  Fall back to score-based determination (>= 7.0 is GO)
    since the prompt instructs the agent to use that threshold.
    """
    if not response:
        return "NO-GO", "No response from focus group"

    import re

    # Extract overall score if present
    score = None
    for line in response.split("\n"):
        line_lower = line.lower().strip()
        if "overall" in line_lower and ("score" in line_lower or "weighted" in line_lower):
            numbers = re.findall(r'(\d+\.?\d*)\s*/?\s*10', line)
            if numbers:
                score = float(numbers[0])
                break
            numbers = re.findall(r'(\d+\.?\d*)', line)
            if numbers:
                score = float(numbers[-1])
                break

    # Find the Go/No-Go Recommendation section specifically
    # to avoid matching criteria text or earlier mentions
    recommendation_section = ""
    lines = response.split("\n")
    in_recommendation = False
    for line in lines:
        line_lower = line.lower().strip()
        if "go/no-go" in line_lower and ("recommendation" in line_lower or "###" in line_lower):
            in_recommendation = True
            continue
        if in_recommendation:
            # Stop at next section header
            if line.strip().startswith("###") or line.strip().startswith("## "):
                break
            recommendation_section += line + "\n"

    # Check the recommendation section for the verdict
    if recommendation_section:
        rec_lower = recommendation_section.lower()
        # In the recommendation section, check for NO-GO first
        has_nogo_rec = "**no-go**" in rec_lower or "no-go" in rec_lower.split("recommendation")[-1] if "recommendation" in rec_lower else "no-go" in rec_lower
        has_go_rec = "**go**" in rec_lower

        # If both appear, look at the LAST occurrence to get the actual verdict
        if has_nogo_rec and has_go_rec:
            last_nogo = rec_lower.rfind("no-go")
            last_go = rec_lower.rfind("**go**")
            if last_go > last_nogo:
                has_nogo_rec = False
            else:
                has_go_rec = False

        if has_nogo_rec:
            reason = "Focus group gave NO-GO"
            if score is not None:
                reason += f" (overall score: {score}/10)"
            return "NO-GO", reason
        elif has_go_rec:
            reason = "Focus group gave GO"
            if score is not None:
                reason += f" (overall score: {score}/10)"
            return "GO", reason

    # Fallback: use the score threshold (prompt says >= 7.0 is GO)
    if score is not None:
        if score >= 7.0:
            reason = f"Focus group gave GO (score-based: {score}/10 >= 7.0)"
            return "GO", reason
        else:
            reason = f"Focus group gave NO-GO (score-based: {score}/10 < 7.0)"
            return "NO-GO", reason

    return "UNCLEAR", f"Could not determine GO/NO-GO from response (score: {score})"


# ===================================================================
# Pipeline steps
# ===================================================================

def step_1_greeting(session_id):
    """Say hello."""
    print("\n\n--- STEP 1: Greeting ---")
    response, tools = send_message(session_id, "hello", timeout=SHORT_TIMEOUT)
    if response is None:
        print("[FAIL] No response to greeting")
        return False
    if "KeyError" in (response or "") or "Context variable not found" in (response or ""):
        print("[FAIL] KeyError detected in greeting response!")
        return False
    print("[PASS] Greeting OK")
    return True


def step_2_campaign_metadata(session_id):
    """Provide campaign metadata."""
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
    return True


def step_3_auto_select_trends(session_id):
    """Auto-select trends."""
    print("\n\n--- STEP 3: Auto-Select Trends ---")
    response, tools = send_message(
        session_id,
        (
            "Auto-select the best trends for this campaign. "
            "Pick brand-safe Google Search and YouTube trends "
            "relevant to McDonald's McRib and Shamrock Shake for Senior Citizens. "
            "After selecting, immediately save them using "
            "save_search_trends_to_session_state and save_yt_trends_to_session_state."
        ),
        timeout=MEDIUM_TIMEOUT,
    )

    search_saved = check_state_key(session_id, "target_search_trends")
    yt_saved = check_state_key(session_id, "target_yt_trends")

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
        search_saved = check_state_key(session_id, "target_search_trends")
        yt_saved = check_state_key(session_id, "target_yt_trends")

    return search_saved and yt_saved


def step_4_research(session_id):
    """Confirm and proceed to research."""
    print("\n\n--- STEP 4: Confirm Selections -> Research ---")
    response, tools = send_message(
        session_id,
        "Looks great, proceed with research.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(session_id, "combined_final_cited_report"):
        print("  Waiting for research to complete...")
        response, tools = send_message(
            session_id,
            "Please continue with the research pipeline",
            timeout=LONG_TIMEOUT,
        )
        check_state_key(session_id, "combined_final_cited_report")

    return check_state_key(session_id, "combined_final_cited_report")


def step_5_ad_generation(session_id):
    """Proceed to ad generation."""
    print("\n\n--- STEP 5: Report -> Ad Generation ---")
    response, tools = send_message(
        session_id,
        "Report looks good, proceed to ad generation.",
        timeout=LONG_TIMEOUT,
    )

    if not check_state_key(session_id, "ad_copy_critique"):
        response, tools = send_message(
            session_id,
            "Please generate the ad copies",
            timeout=LONG_TIMEOUT,
        )

    return True


def step_6_select_ad_copies(session_id):
    """Select ad copies."""
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

    if not check_state_key(session_id, "final_select_ad_copies"):
        response, tools = send_message(
            session_id,
            (
                "Please save ad copies 1, 2, and 3 using the save_select_ad_copy tool. "
                "Call save_select_ad_copy once for each ad copy."
            ),
            timeout=MEDIUM_TIMEOUT,
        )

    return check_state_key(session_id, "final_select_ad_copies")


def step_7_visual_pipeline(session_id):
    """Visual generation pipeline."""
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

    if not check_state_key(session_id, "final_visual_concepts"):
        response, tools = send_message(
            session_id,
            "Please continue with the visual concept generation",
            timeout=LONG_TIMEOUT,
        )

    return True


def step_8_select_visual_concepts(session_id):
    """Select visual concepts."""
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

    if not check_state_key(session_id, "final_select_vis_concepts"):
        response, tools = send_message(
            session_id,
            (
                "Please use the save_select_visual_concept tool to save at least "
                "2 visual concepts: one with type 'image' and one with type 'video'. "
                "Call save_select_visual_concept once per concept."
            ),
            timeout=MEDIUM_TIMEOUT,
        )

    return check_state_key(session_id, "final_select_vis_concepts")


def step_9_generate_visuals(session_id):
    """Generate visuals (Imagen + Veo)."""
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

    return True


def step_10_save_report(session_id):
    """Save creatives report."""
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
        response, tools = send_message(
            session_id,
            (
                "You need to call the save_creatives_and_research_report tool right now. "
                "This is step 4 in the root_agent workflow. Just call the tool -- "
                "do not explain, just execute it."
            ),
            timeout=LONG_TIMEOUT,
        )

    return True


def step_11_av_studio(session_id):
    """Run the AV editing studio pipeline. Returns True if commercial_artifact is saved."""
    # --- Step 11a: Storyboard + Subject Images ---
    print("\n\n--- STEP 11a: Storyboard + Subject Images ---")
    response, tools = send_message(
        session_id,
        (
            "Now proceed to step 5: transfer to the av_editing_studio_agent sub-agent. "
            "The AV studio should produce a 30-second commercial. "
            "Start by planning the 4-scene storyboard for McRib and Shamrock Shake "
            "targeting Senior Citizens, connecting the selected trends to the product. "
            "Create a detailed CHARACTER SHEET and PRODUCT SHEET. "
            "Then call generate_subject_image for the primary character (at least 2 angles) "
            "and product reference. Use these reference images for character consistency "
            "by passing them as reference_image_gcs_uris to every generate_clip_with_frames call."
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
                "at least 2 reference images for the primary character (front-facing and "
                "3/4 angle) and 1 for the product. These will be used as "
                "reference_image_gcs_uris in all clip generation calls."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # Check if the agent already completed the full pipeline
    commercial_saved = check_state_key(session_id, "commercial_artifact")
    if commercial_saved:
        print("  [SKIP] Agent completed full pipeline in one turn")
        return True

    # --- Step 11b: Generate Clips 1 & 2 ---
    print("\n\n--- STEP 11b: Generate Clips 1 & 2 ---")
    response, tools = send_message(
        session_id,
        (
            "Now generate the first 2 clips of the commercial:\n"
            "1. Call generate_clip_with_frames for Clip 1 (Hook scene) using the "
            "subject image as first_frame_gcs_uri and ALL subject reference image "
            "GCS URIs as reference_image_gcs_uris.\n"
            "2. Call extract_frame_from_clip on Clip 1 to get the last frame.\n"
            "3. Call generate_clip_with_frames for Clip 2 (Connection scene) using "
            "that last frame as first_frame_gcs_uri and ALL reference_image_gcs_uris.\n"
            "Execute these now."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    if "generate_clip_with_frames" not in tools:
        print("  [RETRY] Clips 1&2 not started, retrying...")
        response, tools = send_message(
            session_id,
            (
                "Please start generating Clip 1 now using generate_clip_with_frames. "
                "Use the subject image GCS URI as first_frame_gcs_uri and pass all "
                "reference image GCS URIs as reference_image_gcs_uris for character "
                "consistency. After Clip 1 finishes, extract its last frame and generate Clip 2."
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
            "2. Call generate_clip_with_frames for Clip 3 (Demonstration scene) "
            "with reference_image_gcs_uris.\n"
            "3. Extract the last frame of Clip 3.\n"
            "4. Call generate_clip_with_frames for Clip 4 (Resolution scene) "
            "with reference_image_gcs_uris.\n"
            "Execute these now."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    if "generate_clip_with_frames" not in tools and "extract_frame_from_clip" not in tools:
        print("  [RETRY] Clips 3&4 not started, retrying...")
        response, tools = send_message(
            session_id,
            (
                "Please continue generating the remaining clips. Extract the last "
                "frame from the most recent clip and use it as first_frame_gcs_uri "
                "for the next clip. Pass reference_image_gcs_uris for character "
                "consistency. Generate clips until you have 4 total."
            ),
            timeout=EXTRA_LONG_TIMEOUT,
        )

    # --- Step 11d: Assembly (concatenate + trim + save) ---
    print("\n\n--- STEP 11d: Concatenate, Trim & Save ---")
    commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
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
        print("  [RETRY] Final attempt at save...")
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

    return commercial_saved


def step_12_focus_group(session_id):
    """Run focus group evaluation. Returns (verdict, reason, response)."""
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

    analyze_called = "analyze_commercial_video" in tools
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

    verdict, reason = extract_focus_group_verdict(response)
    print(f"\n  [FOCUS GROUP] Verdict: {verdict}")
    print(f"  [FOCUS GROUP] Reason: {reason}")
    return verdict, reason, response


def step_11_retry_av_studio(session_id, previous_feedback):
    """Re-run the AV studio with feedback from the focus group."""
    print("\n\n--- RETRY AV STUDIO: Regenerating commercial with feedback ---")

    response, tools = send_message(
        session_id,
        (
            f"The focus group evaluation came back as NO-GO. Here's the feedback:\n\n"
            f"{previous_feedback[:1500]}\n\n"
            "Please transfer back to the av_editing_studio_agent sub-agent and "
            "regenerate the 30-second commercial addressing the focus group's concerns. "
            "Keep the same campaign metadata and trends, but improve the storyboard, "
            "character consistency, and narrative based on the feedback above. "
            "Make sure to:\n"
            "1. Create a new storyboard with an improved CHARACTER SHEET\n"
            "2. Generate new subject reference images (at least 2 angles for the character)\n"
            "3. Generate all 4 clips with reference_image_gcs_uris for character consistency\n"
            "4. Concatenate, trim to 30s, and save_commercial_artifact\n"
            "Start now."
        ),
        timeout=EXTRA_LONG_TIMEOUT,
    )

    # Follow the same assembly flow
    commercial_saved = check_state_key(session_id, "commercial_artifact")

    if not commercial_saved:
        # Keep nudging
        for attempt in range(3):
            if commercial_saved:
                break
            response, tools = send_message(
                session_id,
                (
                    "Please continue with the AV studio pipeline. Generate all remaining "
                    "clips, then concatenate, trim to 30s, and call save_commercial_artifact. "
                    "Do not stop until save_commercial_artifact is called."
                ),
                timeout=EXTRA_LONG_TIMEOUT,
            )
            commercial_saved = check_state_key(session_id, "commercial_artifact")

    return commercial_saved


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("RALPH WIGGUM E2E TEST")
    print("McDonald's / McRib + Shamrock Shake / Senior Citizens / 30s Commercial")
    print("Goal: Full pipeline -> Focus group GO")
    print(f"Max AV iterations: {MAX_AV_ITERATIONS}")
    print("=" * 70)

    # Initialize Ralph Loop
    ralph = RalphLoop(
        goal="Create a 30s commercial that passes focus group evaluation",
        promise="Focus group returns GO recommendation",
        max_iterations=MAX_AV_ITERATIONS,
    )

    # Step 0: Create session
    session_id = create_session()

    # Steps 1-10: One-time pipeline setup (not iterated)
    if not step_1_greeting(session_id):
        print("[ABORT] Greeting failed")
        sys.exit(1)

    step_2_campaign_metadata(session_id)

    if not step_3_auto_select_trends(session_id):
        print("[WARN] Trends may not be fully saved, continuing anyway")

    step_4_research(session_id)
    step_5_ad_generation(session_id)
    step_6_select_ad_copies(session_id)
    step_7_visual_pipeline(session_id)
    step_8_select_visual_concepts(session_id)
    step_9_generate_visuals(session_id)
    step_10_save_report(session_id)

    # ===================================================================
    # Ralph Loop: AV Studio + Focus Group (iterate until GO)
    # ===================================================================
    focus_group_response = None

    while not ralph.is_done() and ralph.can_continue():
        if ralph.current == 0:
            # First iteration: fresh AV studio run
            ralph.start_iteration("Run AV studio pipeline (first attempt)")
            commercial_saved = step_11_av_studio(session_id)
        else:
            # Subsequent iterations: re-run with feedback
            ralph.start_iteration(f"Re-run AV studio with focus group feedback (attempt {ralph.current + 1})")
            commercial_saved = step_11_retry_av_studio(session_id, focus_group_response or "")

        if not commercial_saved:
            ralph.end_iteration("commercial_artifact not saved", "FAILED")
            continue

        # Run focus group
        verdict, reason, focus_group_response = step_12_focus_group(session_id)

        if verdict == "GO":
            ralph.end_iteration(reason, "PASSED")
        elif verdict == "NO-GO":
            ralph.end_iteration(reason, "FAILED")
        else:
            # UNCLEAR -- treat as progress if score is available
            ralph.end_iteration(reason, "PROGRESS")

    # ===================================================================
    # Final Verification
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

    # Commercial artifact
    commercial = state.get("commercial_artifact", {})
    commercial_pass = bool(commercial and commercial.get("artifact_key"))
    commercial_duration = commercial.get("metadata", {}).get("duration_seconds", 0)
    duration_pass = commercial_duration == 30
    print(f"  [{'PASS' if commercial_pass else 'FAIL'}] commercial_artifact")
    print(f"  [{'PASS' if duration_pass else 'WARN'}] commercial_artifact.duration_seconds == 30 (actual: {commercial_duration})")

    # Ralph Loop Summary
    final_status = ralph.summary()

    print(f"\n{'='*70}")
    if final_status == "PASSED":
        print("RALPH WIGGUM E2E TEST: PASSED")
        print(f"  Commercial produced and focus group gave GO in {ralph.current} iteration(s)")
    else:
        print(f"RALPH WIGGUM E2E TEST: FAILED after {ralph.current} iteration(s)")
        print(f"  Focus group never gave GO recommendation")
    print(f"{'='*70}")

    return 0 if final_status == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
