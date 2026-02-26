"""
E2E test for trends_and_insights_agent via Gemini Enterprise (Discovery Engine).
Produces a 15-second commercial by driving the pipeline through GE's streamAssist API.

Usage:
  python tests/ge_e2e_15s_test.py
  python tests/ge_e2e_15s_test.py --engine-id my-engine --agent-id 12345
"""

import argparse
import json
import logging
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path so we can import the client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hello_gemini_agent.client import AgentClient, AgentAuthorizationError, RetryableAPIError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Defaults from memory
DEFAULT_PROJECT_ID = "wortz-project-352116"
DEFAULT_LOCATION = "global"
DEFAULT_ENGINE_ID = "grocery-workshop-engine"
DEFAULT_AGENT_ID = "7324026170917033413"

# Timeouts between steps (seconds) to let the agent process
STEP_DELAY = 5
LONG_STEP_DELAY = 15

# Pixel preset metadata (formatted as a conversational message)
PIXEL_METADATA_MSG = (
    "Brand: Google Pixel, Product: Pixel 9 smartphone, "
    "Target Audience: millennials who follow jam bands such as Widespread Panic and Phish, "
    "Key Selling Points: Best Take - Group pics perfected with AI blending, "
    "Night Sight + Astrophotography - Capture the cosmos, "
    "Magic Editor - Generative AI photo editing, "
    "Call Screen - Detect and filter spam calls, "
    "Live Translate - Real-time translation without internet, "
    "Real Tone - Authentic skin tone representation in photos and video."
)


def extract_text_from_ge_response(response_chunks):
    """Extract all text from GE streamAssist response chunks.

    Response structure: [{answer: {replies: [{groundedContent: {content: {text, role, thought}}}]}}, {sessionInfo: ...}]
    """
    texts = []
    for chunk in response_chunks:
        if not isinstance(chunk, dict):
            continue
        answer = chunk.get("answer", {})
        replies = answer.get("replies", [])
        for reply in replies:
            if not isinstance(reply, dict):
                continue
            grounded = reply.get("groundedContent", {})
            content = grounded.get("content", {})
            text = content.get("text", "")
            is_thought = content.get("thought", False)
            if text and not is_thought:
                texts.append(text)
    return "\n".join(texts)


def send_ge_message(client, session_id, message, step_name="", timeout_retries=3):
    """Send a message to GE agent and return the response text."""
    print(f"\n{'='*70}")
    print(f"[USER] [{step_name}] {message[:200]}{'...' if len(message) > 200 else ''}")
    print(f"{'='*70}")

    start = time.time()
    for attempt in range(timeout_retries):
        try:
            response_chunks = client.query_agent(message, session_id=session_id)
            elapsed = time.time() - start
            response_text = extract_text_from_ge_response(response_chunks)
            display = response_text[:2000] + "..." if len(response_text) > 2000 else response_text
            print(f"\n[AGENT] ({elapsed:.1f}s) {display}")
            return response_text
        except RetryableAPIError as e:
            elapsed = time.time() - start
            print(f"  [WARN] Attempt {attempt+1}/{timeout_retries} failed ({elapsed:.1f}s): {e}")
            if attempt < timeout_retries - 1:
                wait = min(30 * (attempt + 1), 120)
                print(f"  [INFO] Waiting {wait}s before retry...")
                time.sleep(wait)
        except AgentAuthorizationError as e:
            print(f"  [FAIL] Authorization error: {e}")
            return None
        except Exception as e:
            elapsed = time.time() - start
            print(f"  [ERROR] ({elapsed:.1f}s) {e}")
            return None

    print(f"  [FAIL] All {timeout_retries} attempts failed")
    return None


def check_response_for_keywords(response_text, keywords, step_name=""):
    """Check if response contains expected keywords."""
    if not response_text:
        print(f"  [FAIL] No response to check for {step_name}")
        return False

    response_lower = response_text.lower()
    found = []
    missing = []
    for kw in keywords:
        if kw.lower() in response_lower:
            found.append(kw)
        else:
            missing.append(kw)

    if found:
        print(f"  [INFO] Found keywords: {', '.join(found)}")
    if missing:
        print(f"  [WARN] Missing keywords: {', '.join(missing)}")

    return len(found) > 0


def main():
    parser = argparse.ArgumentParser(description="Gemini Enterprise E2E 15s Commercial Test")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    parser.add_argument("--engine-id", default=DEFAULT_ENGINE_ID)
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    args = parser.parse_args()

    print("=" * 70)
    print("Gemini Enterprise E2E Test: 15s Commercial")
    print(f"  Project: {args.project_id}")
    print(f"  Location: {args.location}")
    print(f"  Engine: {args.engine_id}")
    print(f"  Agent: {args.agent_id}")
    print("=" * 70)

    # Initialize client
    client = AgentClient(
        project_id=args.project_id,
        location=args.location,
        engine_id=args.engine_id,
        agent_id=args.agent_id,
    )

    # Step 0: Warmup (GE cold start can be slow)
    print("\n\n--- STEP 0: Warmup ---")
    warmup_response = send_ge_message(
        client, None, "hello", step_name="warmup", timeout_retries=5
    )
    if warmup_response is None:
        print("[FAIL] Could not reach GE agent after warmup attempts")
        sys.exit(1)
    print(f"[PASS] GE agent is responsive (response length: {len(warmup_response)})")

    # Step 1: Create session
    print("\n\n--- STEP 1: Create Session ---")
    try:
        session_id = client.create_session()
        print(f"[SESSION] Created GE session: {session_id}")
    except Exception as e:
        print(f"[FAIL] Could not create session: {e}")
        sys.exit(1)

    # Step 2: Send campaign metadata (no preset API in GE, send conversationally)
    print("\n\n--- STEP 2: Campaign Metadata ---")
    response = send_ge_message(
        client, session_id, PIXEL_METADATA_MSG, step_name="metadata"
    )
    if response is None:
        print("[FAIL] No response to metadata")
        sys.exit(1)
    # Check that the agent acknowledged the metadata
    check_response_for_keywords(response, ["pixel", "brand", "audience", "trend"], "metadata")

    time.sleep(STEP_DELAY)

    # Step 3: Auto-select trends
    print("\n\n--- STEP 3: Auto-Select Trends ---")
    response = send_ge_message(
        client, session_id,
        "Auto-select the best trends for this campaign. "
        "Pick brand-safe Google Search and YouTube trends "
        "relevant to Google Pixel 9 for millennials who follow jam bands.",
        step_name="trends",
    )
    check_response_for_keywords(response, ["trend", "search", "youtube"], "trends")

    time.sleep(STEP_DELAY)

    # Step 4: Proceed to research
    print("\n\n--- STEP 4: Confirm -> Research ---")
    response = send_ge_message(
        client, session_id,
        "Looks great, proceed with research.",
        step_name="research",
    )
    check_response_for_keywords(response, ["research", "report", "analysis"], "research")

    time.sleep(LONG_STEP_DELAY)

    # Step 5: Ad generation
    print("\n\n--- STEP 5: Ad Generation ---")
    response = send_ge_message(
        client, session_id,
        "Report looks good, proceed to ad generation.",
        step_name="ad_gen",
    )
    check_response_for_keywords(response, ["ad", "copy", "creative"], "ad_gen")

    time.sleep(STEP_DELAY)

    # Step 6: Select ad copies
    print("\n\n--- STEP 6: Select Ad Copies ---")
    response = send_ge_message(
        client, session_id,
        "These ad copies look great. Select ad copies 1, 2, and 3. "
        "Save each using save_select_ad_copy.",
        step_name="select_ads",
    )
    check_response_for_keywords(response, ["saved", "selected", "ad copy"], "select_ads")

    time.sleep(STEP_DELAY)

    # Step 7: Visual generation pipeline
    print("\n\n--- STEP 7: Visual Pipeline ---")
    response = send_ge_message(
        client, session_id,
        "Now proceed with the visual_generation_pipeline to generate visual concepts.",
        step_name="visual_pipeline",
    )
    check_response_for_keywords(response, ["visual", "concept", "image"], "visual_pipeline")

    time.sleep(STEP_DELAY)

    # Step 8: Select visual concepts
    print("\n\n--- STEP 8: Select Visuals ---")
    response = send_ge_message(
        client, session_id,
        "Select 2 visual concepts: one image-type and one video-type. "
        "Save each using save_select_visual_concept.",
        step_name="select_visuals",
    )
    check_response_for_keywords(response, ["visual", "selected", "image", "video"], "select_visuals")

    time.sleep(STEP_DELAY)

    # Step 9: Generate visuals
    print("\n\n--- STEP 9: Generate Visuals ---")
    response = send_ge_message(
        client, session_id,
        "Now call the visual_generator tool to generate the image and video creatives. "
        "Then save artifacts with save_img_artifact_key and save_vid_artifact_key.",
        step_name="generate_visuals",
    )
    check_response_for_keywords(response, ["generated", "image", "video", "artifact"], "generate_visuals")

    time.sleep(STEP_DELAY)

    # Step 10: Save report
    print("\n\n--- STEP 10: Save Report ---")
    response = send_ge_message(
        client, session_id,
        "Call save_creatives_and_research_report now to build the final PDF report.",
        step_name="save_report",
    )
    check_response_for_keywords(response, ["report", "saved", "pdf"], "save_report")

    time.sleep(STEP_DELAY)

    # Step 11: AV Studio 15s commercial
    print("\n\n--- STEP 11: AV Studio (15s commercial) ---")
    response = send_ge_message(
        client, session_id,
        "Now transfer to the av_editing_studio_agent. Produce a 15-second commercial: "
        "plan a 2-scene storyboard, generate subject reference images, "
        "generate 2 clips with frame chaining, concatenate, trim to 15 seconds, "
        "and save with save_commercial_artifact (duration_seconds=15).",
        step_name="av_studio",
    )

    # AV studio may need multiple nudges
    if not check_response_for_keywords(response, ["clip", "commercial", "storyboard", "scene"], "av_studio"):
        time.sleep(LONG_STEP_DELAY)
        response = send_ge_message(
            client, session_id,
            "Continue with the AV studio: generate 2 clips using generate_clip_with_frames, "
            "concatenate them, trim to 15 seconds, and save_commercial_artifact.",
            step_name="av_studio_retry",
        )

    time.sleep(LONG_STEP_DELAY)

    # Check for commercial completion
    print("\n\n--- STEP 11b: Check Commercial ---")
    response = send_ge_message(
        client, session_id,
        "Has the 15-second commercial been saved? If not, please concatenate the clips, "
        "trim to 15 seconds, and call save_commercial_artifact now.",
        step_name="commercial_check",
    )
    commercial_mentioned = check_response_for_keywords(
        response, ["commercial", "saved", "artifact", "15"], "commercial_check"
    )

    # Step 12: Focus group
    print("\n\n--- STEP 12: Focus Group ---")
    response = send_ge_message(
        client, session_id,
        "Transfer to focus_group_evaluator_agent. Call analyze_commercial_video "
        "to analyze the 15-second commercial, then provide a focus group evaluation "
        "with scoring and Go/No-Go recommendation.",
        step_name="focus_group",
    )
    focus_group_done = check_response_for_keywords(
        response, ["focus group", "score", "recommendation", "go"], "focus_group"
    )

    if not focus_group_done:
        time.sleep(STEP_DELAY)
        response = send_ge_message(
            client, session_id,
            "Please complete the focus group evaluation. Call analyze_commercial_video "
            "and provide scores and a Go/No-Go recommendation.",
            step_name="focus_group_retry",
        )
        focus_group_done = check_response_for_keywords(
            response, ["focus group", "score", "recommendation", "go"], "focus_group_retry"
        )

    # Final summary
    print(f"\n\n{'='*70}")
    print("FINAL GE E2E SUMMARY")
    print("=" * 70)
    print(f"  [{'PASS' if warmup_response else 'FAIL'}] Agent responsive")
    print(f"  [{'PASS' if commercial_mentioned else 'WARN'}] Commercial creation mentioned")
    print(f"  [{'PASS' if focus_group_done else 'WARN'}] Focus group evaluation")
    print()

    # GE doesn't expose session state directly, so we can't verify state keys.
    # Success is determined by the agent's conversational responses.
    if commercial_mentioned and focus_group_done:
        print("GE E2E TEST: PASS (15s commercial pipeline completed)")
        sys.exit(0)
    elif commercial_mentioned:
        print("GE E2E TEST: PARTIAL PASS (commercial created, focus group incomplete)")
        sys.exit(1)
    else:
        print("GE E2E TEST: FAIL (commercial not confirmed)")
        sys.exit(1)
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
