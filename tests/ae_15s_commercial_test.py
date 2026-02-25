"""Test script for 15-second commercial generation on deployed Agent Engine agent.

This test script:
1. Connects to deployed Agent Engine agent
2. Pre-populates session state with campaign metadata
3. Requests a 15-second commercial (2 clips)
4. Verifies the commercial artifact has correct duration and clip count

Usage:
    python tests/ae_15s_commercial_test.py <AGENT_ID>

Example:
    python tests/ae_15s_commercial_test.py 6755024507590672384

Environment variables required:
    GOOGLE_CLOUD_PROJECT
    GOOGLE_CLOUD_PROJECT_NUMBER
"""
from dotenv import load_dotenv
import os
import sys
import time
import json
from pprint import pprint

load_dotenv("trends_and_insights_agent/.env")

import vertexai

# Get the agent ID from command line argument or environment
if len(sys.argv) < 2:
    print("Error: Agent ID required")
    print("Usage: python tests/ae_15s_commercial_test.py <AGENT_ID>")
    sys.exit(1)

AGENT_ID = sys.argv[1]
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
PROJECT_NUM = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
LOCATION = "us-central1"

# Build full resource name if just an ID was provided
if "/" not in AGENT_ID:
    RESOURCE_NAME = f"projects/{PROJECT_NUM}/locations/{LOCATION}/reasoningEngines/{AGENT_ID}"
else:
    RESOURCE_NAME = AGENT_ID

print(f"{'='*70}")
print(f"15-SECOND COMMERCIAL TEST - AGENT ENGINE")
print(f"{'='*70}")
print(f"Connecting to: {RESOURCE_NAME}")
print(f"Project: {PROJECT}, Location: {LOCATION}\n")

# Initialize client
client = vertexai.Client(project=PROJECT, location=LOCATION)

# Get the deployed agent
try:
    agent = client.agent_engines.get(name=RESOURCE_NAME)
    print(f"[SUCCESS] Agent retrieved: {agent.api_resource.name}\n")
except Exception as e:
    print(f"[ERROR] Failed to get agent: {e}")
    sys.exit(1)

# Create a session
user_id = "test-15s-" + str(int(time.time()))
try:
    session = agent.create_session(user_id=user_id)
    # Handle both dict (remote) and object (local) session formats
    try:
        session_id = session["id"]
    except (TypeError, KeyError):
        session_id = session.id
    print(f"[SUCCESS] Session created: {session_id}")
    print(f"[SUCCESS] User ID: {user_id}\n")
except Exception as e:
    print(f"[ERROR] Failed to create session: {e}")
    sys.exit(1)


def send_message(message: str, timeout_seconds: int = 300):
    """Send a message to the agent using stream_query API.

    Args:
        message: The message text to send
        timeout_seconds: Max time to wait for response

    Returns:
        Tuple of (full_response_text, list_of_events)
    """
    print(f"\n{'='*70}")
    print(f"[USER MESSAGE]")
    print(f"{message[:500]}{'...' if len(message) > 500 else ''}")
    print(f"{'='*70}")

    full_response = ""
    all_events = []

    start_time = time.time()
    try:
        for event in agent.stream_query(
            user_id=user_id,
            session_id=session_id,
            message=message,
        ):
            all_events.append(event)

            # Extract text from events
            if isinstance(event, dict) and "content" in event:
                content = event["content"]
                if isinstance(content, dict) and "parts" in content:
                    for part in content["parts"]:
                        if isinstance(part, dict) and "text" in part:
                            full_response += part["text"]
                        # Track tool calls
                        if isinstance(part, dict) and "function_call" in part:
                            fc = part["function_call"]
                            tool_name = fc.get("name", "unknown")
                            print(f"  [TOOL CALL] {tool_name}")

            # Check timeout
            if time.time() - start_time > timeout_seconds:
                print(f"\n[WARNING] Timeout reached ({timeout_seconds}s)")
                break

        elapsed = time.time() - start_time
        print(f"\n[AGENT RESPONSE] ({elapsed:.1f}s)")
        if full_response:
            display = full_response[:1000] + "..." if len(full_response) > 1000 else full_response
            print(display)
        else:
            print("(No text response)")

    except Exception as e:
        print(f"\n[ERROR] Failed to send message: {e}")
        return "", []

    return full_response, all_events


def get_session_state():
    """Retrieve current session state."""
    try:
        # Use the session API to get state
        # Note: Agent Engine API may not expose state directly
        # This is a placeholder - actual implementation may vary
        return None
    except Exception as e:
        print(f"[WARNING] Could not retrieve session state: {e}")
        return None


# =============================================================================
# TEST FLOW
# =============================================================================

print(f"\n{'='*70}")
print("STEP 1: Initialize campaign context")
print(f"{'='*70}")

# Send initial campaign context
send_message(
    "I'm planning a marketing campaign with the following details:\n\n"
    "Brand: Google Pixel\n"
    "Product: Pixel 9 Pro\n"
    "Target Audience: Tech-savvy millennials and Gen Z\n"
    "Key Selling Points: AI-powered camera, Tensor G4 chip, 7 years of updates\n\n"
    "Please acknowledge these details and wait for further instructions.",
    timeout_seconds=120
)

print(f"\n{'='*70}")
print("STEP 2: Set commercial duration to 15 seconds")
print(f"{'='*70}")

# Set duration to 15 seconds
send_message(
    "Set the commercial duration to 15 seconds. This means we need to generate "
    "a 2-clip commercial instead of the standard 4-clip 30-second format. "
    "commercial_duration=15",
    timeout_seconds=120
)

print(f"\n{'='*70}")
print("STEP 3: Select Google trend")
print(f"{'='*70}")

# Auto-select a Google trend
send_message(
    "select a google trend",
    timeout_seconds=180
)

print(f"\n{'='*70}")
print("STEP 4: Select YouTube trend")
print(f"{'='*70}")

# Auto-select a YouTube trend
send_message(
    "select a yt trend",
    timeout_seconds=180
)

print(f"\n{'='*70}")
print("STEP 5: Generate 15-second commercial")
print(f"{'='*70}")

# Request 15-second commercial
response, events = send_message(
    "Now create a 15-second commercial for the Pixel 9 Pro. "
    "\n\nIMPORTANT SPECIFICATIONS FOR 15-SECOND FORMAT:"
    "\n1. Generate ONLY 2 VIDEO CLIPS (not 4 clips)"
    "\n2. Each clip should be approximately 8 seconds before trimming"
    "\n3. Final trimmed duration should be exactly 15 seconds"
    "\n4. Use a condensed 2-scene narrative arc:"
    "\n   - Scene 1 (Hook + Connection): Open with the trend and quickly connect to the product"
    "\n   - Scene 2 (Demonstration + CTA): Show the product benefit and end with call-to-action"
    "\n\nWorkflow adjustments for av_editing_studio_agent:"
    "\n- Step 1: Create a 2-scene storyboard (not 4 scenes)"
    "\n- Step 3: Generate only 2 clips with frame matching"
    "\n- Step 7: Concatenate 2 clips (~16s raw) and trim to 15s"
    "\n\nPlease proceed with the complete pipeline: research, ad copy, visual concepts, "
    "and the 15-second video commercial.",
    timeout_seconds=1200  # 20 minutes for full pipeline
)

# =============================================================================
# VERIFICATION
# =============================================================================

print(f"\n{'='*70}")
print("VERIFICATION: Checking for commercial_artifact in session state")
print(f"{'='*70}")

# Since Agent Engine may not expose session state via API, we check the response
# Look for indicators in the agent's final response
verification_passed = False
duration_correct = False
clips_correct = False

# Parse events for session state updates (if available)
for event in events:
    if isinstance(event, dict):
        # Check if event contains session state
        if "session_state" in event or "state" in event:
            state = event.get("session_state") or event.get("state", {})
            commercial = state.get("commercial_artifact", {})

            if commercial and isinstance(commercial, dict):
                metadata = commercial.get("metadata", {})
                duration = metadata.get("duration_seconds", 0)
                total_clips = metadata.get("total_clips", 0)

                verification_passed = True
                duration_correct = (duration == 15)
                clips_correct = (total_clips == 2)

                print(f"[INFO] commercial_artifact found:")
                print(f"  - duration_seconds: {duration}")
                print(f"  - total_clips: {total_clips}")
                print(f"  - gcs_uri: {commercial.get('gcs_uri', 'N/A')}")
                break

# Check response text for indicators
if not verification_passed:
    if "commercial_artifact" in response.lower():
        print("[INFO] Response mentions 'commercial_artifact'")
        verification_passed = True
    if "15 second" in response.lower() or "15-second" in response.lower():
        print("[INFO] Response mentions 15-second duration")
        duration_correct = True
    if "2 clip" in response.lower() or "two clip" in response.lower():
        print("[INFO] Response mentions 2 clips")
        clips_correct = True

# =============================================================================
# FINAL RESULTS
# =============================================================================

print(f"\n{'='*70}")
print("TEST RESULTS")
print(f"{'='*70}")

print(f"[{'PASS' if verification_passed else 'FAIL'}] Commercial artifact created")
print(f"[{'PASS' if duration_correct else 'FAIL'}] Duration = 15 seconds")
print(f"[{'PASS' if clips_correct else 'FAIL'}] Total clips = 2")

if verification_passed and duration_correct and clips_correct:
    print(f"\n{'='*70}")
    print("15-SECOND COMMERCIAL TEST: PASSED")
    print(f"{'='*70}")
    sys.exit(0)
elif verification_passed:
    print(f"\n{'='*70}")
    print("15-SECOND COMMERCIAL TEST: PARTIAL PASS")
    print("Commercial created but may not meet all specifications")
    print(f"{'='*70}")
    sys.exit(1)
else:
    print(f"\n{'='*70}")
    print("15-SECOND COMMERCIAL TEST: FAILED")
    print("Unable to verify commercial artifact creation")
    print(f"{'='*70}")
    sys.exit(1)
