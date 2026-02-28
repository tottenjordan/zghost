"""Test script for interacting with deployed Agent Engine agent.

Uses the correct API pattern from tests/ae_e2e_mcd_test.py and
notebooks/deployment_guide.ipynb.
"""
from dotenv import load_dotenv
import os
import sys
import time
from pprint import pprint

load_dotenv("trends_and_insights_agent/.env")

import vertexai

# Get the agent ID from command line argument or environment
AGENT_ID = sys.argv[1] if len(sys.argv) >= 2 else os.getenv(
    "AGENT_ENGINE_RESOURCE_ID", "6755024507590672384"
)
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
PROJECT_NUM = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER", "679926387543")
LOCATION = "us-central1"

# Build full resource name if just an ID was provided
if "/" not in AGENT_ID:
    RESOURCE_NAME = f"projects/{PROJECT_NUM}/locations/{LOCATION}/reasoningEngines/{AGENT_ID}"
else:
    RESOURCE_NAME = AGENT_ID

print(f"Connecting to: {RESOURCE_NAME}")
print(f"Project: {PROJECT}, Location: {LOCATION}")

# Initialize client
client = vertexai.Client(project=PROJECT, location=LOCATION)

# Get the deployed agent (must use name= keyword arg)
agent = client.agent_engines.get(name=RESOURCE_NAME)
print(f"Agent retrieved: {agent.api_resource.name}")

# Create a session
user_id = "test-user-" + str(int(time.time()))
session = agent.create_session(user_id=user_id)

# Handle both dict (remote) and object (local) session formats
try:
    session_id = session["id"]
except (TypeError, KeyError):
    session_id = session.id
print(f"Session created: {session_id}")


def send_message(message: str):
    """Send a message to the agent using the correct query API."""
    print(f"\n{'='*60}")
    print(f"USER: {message[:200]}{'...' if len(message) > 200 else ''}")
    print(f"{'='*60}")

    # Use stream_query with user_id, session_id, message (verified working pattern)
    full_response = ""
    for event in agent.stream_query(
        user_id=user_id,
        session_id=session_id,
        message=message,
    ):
        pprint(event)
        # Extract text from events
        if isinstance(event, dict) and "content" in event:
            content = event["content"]
            if isinstance(content, dict) and "parts" in content:
                for part in content["parts"]:
                    if isinstance(part, dict) and "text" in part:
                        full_response += part["text"]
        print("---")
    return full_response

# Test 1: Simple greeting
send_message("hello")

# Test 2: Request a 15-second commercial
# The agent needs to be instructed to create 2 clips instead of 4
print("\nNow requesting a 15-second commercial...")
input("Press Enter to continue...")

send_message(
    "I need you to create a 15-second commercial for Google Pixel 9. "
    "\n\nIMPORTANT MODIFICATIONS FOR 15-SECOND FORMAT:"
    "\n1. Generate ONLY 2 VIDEO CLIPS (not 4 clips)"
    "\n2. Each clip should be approximately 8 seconds"
    "\n3. Final trimmed duration should be exactly 15 seconds"
    "\n4. Use a condensed 2-scene narrative arc:"
    "\n   - Scene 1 (Hook + Connection): Open with the trend and quickly connect to the product"
    "\n   - Scene 2 (Demonstration + CTA): Show the product benefit and end with call-to-action"
    "\n\nWorkflow adjustments:"
    "\n- Step 1: Create a 2-scene storyboard (not 4 scenes)"
    "\n- Step 3: Generate only 2 clips with frame matching"
    "\n- Step 7: Concatenate 2 clips (~16s raw) and trim to 15s"
    "\n\nPlease select a trending topic automatically and proceed with the 15-second commercial production."
)

print("\nSession complete!")
print(f"Session ID: {session_id}")
print(f"User ID: {user_id}")
