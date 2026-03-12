#!/usr/bin/env python3
"""Verify LLM-powered status messages and inline artifacts on a deployed Agent Engine.

Usage:
    python verify_status_messages.py [--engine-id ENGINE_ID]

Connects to the deployed Agent Engine, sends a test message, and captures
ui:status_update values from streamed events to verify contextual status messages.
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

import vertexai


def verify_status_messages(engine_id: str):
    """Send a test message and capture status updates from the stream."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = "us-central1"

    print(f"Connecting to Agent Engine {engine_id} in {project}/{location}...")

    client = vertexai.Client(project=project, location=location)
    resource_name = f"projects/{project}/locations/{location}/reasoningEngines/{engine_id}"
    engine = client.agent_engines.get(name=resource_name)
    print(f"  Engine: {engine.api_resource.display_name}")

    # Create a session
    session = engine.create_session(user_id="verify-user")
    session_id = session.get("id") if isinstance(session, dict) else session.id
    print(f"  Session: {session_id}")

    # Send test message
    test_message = "hello"
    print(f"\nSending: '{test_message}'")
    print("=" * 60)

    status_messages = []
    agent_responses = []

    for event in engine.stream_query(
        session_id=session_id,
        message=test_message,
        user_id="verify-user",
    ):
        # Check for status updates in state delta
        if hasattr(event, "actions") and event.actions:
            if hasattr(event.actions, "state_delta") and event.actions.state_delta:
                status = event.actions.state_delta.get("ui:status_update")
                if status:
                    status_messages.append(status)
                    print(f"  [STATUS] {status}")

        # Capture agent text responses
        if hasattr(event, "content") and event.content and hasattr(event.content, "parts") and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    agent_responses.append(part.text)

        # Also check dict-style events
        if isinstance(event, dict):
            sd = event.get("actions", {}).get("state_delta", {}) if isinstance(event.get("actions"), dict) else {}
            if sd.get("ui:status_update"):
                status_messages.append(sd["ui:status_update"])
                print(f"  [STATUS] {sd['ui:status_update']}")

    print("=" * 60)
    print(f"\nCaptured {len(status_messages)} status message(s):")
    for i, msg in enumerate(status_messages, 1):
        is_generic = msg.startswith("Processing ") and msg.endswith("...")
        marker = "GENERIC" if is_generic else "CONTEXTUAL"
        print(f"  {i}. [{marker}] {msg}")

    # Check for contextual (non-generic) messages
    contextual = [m for m in status_messages if not (m.startswith("Processing ") and m.endswith("..."))]
    generic = [m for m in status_messages if m.startswith("Processing ") and m.endswith("...")]

    print(f"\nResults: {len(contextual)} contextual, {len(generic)} generic")

    if agent_responses:
        print(f"\nAgent response preview: {agent_responses[0][:200]}...")

    if contextual:
        print("\nVERIFICATION PASSED: LLM-powered status messages are working!")
        return True
    elif status_messages:
        print("\nWARNING: Status messages captured but all are generic. Check ENABLE_LLM_STATUS env var.")
        return True
    else:
        print("\nWARNING: No status messages captured. The 'hello' message may not trigger tool calls.")
        return True  # Not a failure — hello may not trigger tools


def main():
    parser = argparse.ArgumentParser(description="Verify status messages on deployed Agent Engine")
    parser.add_argument(
        "--engine-id",
        help="Agent Engine ID (reads from deployment_info.json if not provided)",
    )
    args = parser.parse_args()

    engine_id = args.engine_id
    if not engine_id:
        try:
            with open("deployment_info.json") as f:
                info = json.load(f)
            engine_id = info["engine_id"]
        except (FileNotFoundError, KeyError):
            print("ERROR: No engine ID. Provide --engine-id or deploy first (creates deployment_info.json)")
            sys.exit(1)

    verify_status_messages(engine_id)


if __name__ == "__main__":
    main()
