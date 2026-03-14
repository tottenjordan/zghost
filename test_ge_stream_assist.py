"""Test Gemini Enterprise (Agentspace) streamAssist API.

Sends a campaign query via the Discovery Engine streamAssist endpoint
and verifies that the GE assistant routes to the ADK reasoning engine
(not answering directly with generic Gemini knowledge).

Usage:
  # Global endpoint (default for GE)
  uv run python test_ge_stream_assist.py

  # US endpoint
  uv run python test_ge_stream_assist.py --de-location us

  # Custom engine
  uv run python test_ge_stream_assist.py --ge-engine my-engine-id --ge-agent 12345
"""
import argparse
import json
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")

# Read deployment_info.json if available
_deploy_info = {}
if os.path.exists("deployment_info.json"):
    with open("deployment_info.json") as _f:
        _deploy_info = json.load(_f)

# Defaults — override via CLI args or env vars; fall back to deployment_info.json
PROJECT_NUMBER = os.environ.get("GCP_PROJECT_NUMBER", _deploy_info.get("project_number", "679926387543"))

# Discovery Engine (Gemini Enterprise) settings
DE_LOCATION = os.environ.get("DE_LOCATION", "global")  # "global" or "us"
GE_ENGINE = os.environ.get("GE_ENGINE", _deploy_info.get("ge_engine", "gemini-enterprise-17634901_1763490144996"))
GE_AGENT_ID = os.environ.get("GE_AGENT_ID", _deploy_info.get("ge_agent_id", "3607510876288067860"))

# Agent Engine (Reasoning Engine) that GE routes to
AE_ENGINE_ID = os.environ.get("AE_ENGINE_ID", _deploy_info.get("engine_id", "8788263399906607104"))


def get_base_url(de_location: str) -> str:
    """Get the Discovery Engine base URL for the given location."""
    if de_location == "global":
        return "https://global-discoveryengine.googleapis.com"
    return f"https://{de_location}-discoveryengine.googleapis.com"


def get_access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def list_agents(base_url: str, token: str) -> list:
    """List all agents in the GE engine."""
    parent = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
    )
    url = f"{base_url}/v1alpha/{parent}/agents"

    result = subprocess.run(
        ["curl", "-s", "-X", "GET", url,
         "-H", f"Authorization: Bearer {token}",
         "-H", "Content-Type: application/json"],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        print(f"  ERROR parsing agents list: {result.stdout[:200]}")
        return []
    agents = data.get("agents", [])
    print(f"\nFound {len(agents)} agents in {GE_ENGINE}:")
    for a in agents:
        name = a.get("name", "")
        display = a.get("displayName", "")
        agent_id = name.split("/agents/")[-1] if "/agents/" in name else name
        tool_desc = a.get("toolDescription", "")[:80]
        print(f"  - {display} (ID: {agent_id})")
        if tool_desc:
            print(f"    toolDescription: {tool_desc}...")
    return agents


def stream_assist(base_url: str, token: str, query: str, session_id: str = None) -> dict:
    """Call streamAssist on the GE engine."""
    parent = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
    )
    url = f"{base_url}/v1alpha/{parent}/assistants/default_assistant:streamAssist"

    parent = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
    )
    body = {
        "query": {"text": query},
        # Explicit agent routing via agentsSpec (required for reliable routing)
        "agentsSpec": {
            "agentSpecs": [{"agentId": GE_AGENT_ID}]
        },
    }
    if session_id:
        body["session"] = f"{parent}/sessions/{session_id}"
    else:
        body["session"] = f"{parent}/sessions/-"

    result = subprocess.run(
        ["curl", "-s", "-X", "POST", url,
         "-H", f"Authorization: Bearer {token}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(body)],
        capture_output=True, text=True,
        timeout=120,
    )

    print(f"\n{'='*60}")
    print(f"streamAssist query: {query}")
    print(f"{'='*60}")

    # Response is newline-delimited JSON (streaming)
    raw = result.stdout
    if not raw:
        print(f"  ERROR: Empty response. stderr: {result.stderr[:200]}")
        return {}

    # Parse streaming response — may be array or individual JSON objects
    responses = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            responses = parsed
        else:
            responses = [parsed]
    except json.JSONDecodeError:
        # Try line-by-line parsing
        for line in raw.strip().split("\n"):
            line = line.strip().rstrip(",")
            if line.startswith("["):
                line = line[1:]
            if line.endswith("]"):
                line = line[:-1]
            if not line:
                continue
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    # Analyze responses
    routed_to_agent = False
    session_name = None
    reply_text = ""

    for resp in responses:
        # Check for session
        if "session" in resp:
            session_name = resp["session"]

        # Check for reply
        reply = resp.get("reply", {})
        if reply:
            summary = reply.get("summary", {})
            if summary:
                text = summary.get("summaryText", "")
                if text:
                    reply_text += text
                    print(f"  REPLY: {text[:400]}")

                # Check if it references the reasoning engine
                refs = summary.get("references", [])
                for ref in refs:
                    chunk = ref.get("chunkInfo", {})
                    if "reasoningEngine" in str(chunk).lower():
                        routed_to_agent = True

        # Check for agent action
        agent_action = resp.get("agentAction", {})
        if agent_action:
            tool_use = agent_action.get("toolUse", {})
            if tool_use:
                tool_name = tool_use.get("tool", "")
                print(f"  AGENT ACTION: tool={tool_name}")
                if "agent" in tool_name.lower() or str(GE_AGENT_ID) in tool_name:
                    routed_to_agent = True

        # Check for grounding metadata indicating agent routing
        grounding = resp.get("groundingMetadata", {})
        if grounding:
            sources = grounding.get("groundingSources", [])
            for src in sources:
                if "reasoningEngine" in str(src).lower():
                    routed_to_agent = True

    # Extract session ID from session name
    extracted_session_id = None
    if session_name and "/sessions/" in session_name:
        extracted_session_id = session_name.split("/sessions/")[-1]

    print(f"\n  Routed to agent: {'YES' if routed_to_agent else 'NO'}")
    print(f"  Session: {extracted_session_id or 'none'}")
    print(f"  Reply length: {len(reply_text)} chars")

    if not routed_to_agent and reply_text:
        print(f"\n  WARNING: GE may be answering directly (not routing to reasoning engine)")
        print(f"  Check agent toolDescription and ensure it matches the query topic")

    return {
        "routed_to_agent": routed_to_agent,
        "session_id": extracted_session_id,
        "reply_text": reply_text,
        "raw_responses": responses,
    }


def check_agent_config(base_url: str, token: str):
    """Check the specific agent's config to verify reasoning engine mapping."""
    agent_name = (
        f"projects/{PROJECT_NUMBER}/locations/{DE_LOCATION}"
        f"/collections/default_collection/engines/{GE_ENGINE}"
        f"/agents/{GE_AGENT_ID}"
    )
    url = f"{base_url}/v1alpha/{agent_name}"

    result = subprocess.run(
        ["curl", "-s", "-X", "GET", url,
         "-H", f"Authorization: Bearer {token}",
         "-H", "Content-Type: application/json"],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        print(f"  ERROR: Could not parse agent config response: {result.stdout[:200]}")
        print(f"  stderr: {result.stderr[:200]}")
        return {}

    if "error" in data:
        print(f"  API ERROR: {data['error'].get('message', data['error'])}")
        return data

    display = data.get("displayName", "")
    tool_desc = data.get("toolDescription", "")
    vertex_ai = data.get("vertexAiAgentConfig", {})
    reasoning_engine = vertex_ai.get("agent", "")

    print(f"\n--- Agent Config: {display} ---")
    print(f"  Agent ID: {GE_AGENT_ID}")
    print(f"  Reasoning Engine: {reasoning_engine}")
    print(f"  Tool Description: {tool_desc[:200]}")
    print(f"  Expected AE Engine: reasoningEngines/{AE_ENGINE_ID}")

    if str(AE_ENGINE_ID) in reasoning_engine:
        print(f"  Mapping: CORRECT")
    else:
        print(f"  Mapping: MISMATCH — update agent to point to {AE_ENGINE_ID}")

    return data


def main():
    base_url = get_base_url(DE_LOCATION)
    print(f"GE Test — Discovery Engine API")
    print(f"  Location: {DE_LOCATION}")
    print(f"  Base URL: {base_url}")
    print(f"  Engine: {GE_ENGINE}")
    print(f"  Agent: {GE_AGENT_ID}")
    print(f"  AE Engine: {AE_ENGINE_ID}")

    token = get_access_token()

    # Step 1: Check agent config
    check_agent_config(base_url, token)

    # Step 2: List all agents
    list_agents(base_url, token)

    # Step 3: Send a campaign query via streamAssist
    result = stream_assist(
        base_url, token,
        "I want to create a marketing campaign for Tide Fabric Softener with Hibiscus Scent targeting Gen Z consumers.",
    )

    # Step 4: If we got a session, send a follow-up
    if result.get("session_id"):
        stream_assist(
            base_url, token,
            "Select trend 1 for search trends",
            session_id=result["session_id"],
        )

    print(f"\n{'='*60}")
    print("GE STREAM ASSIST TEST COMPLETE")
    print(f"  Routed to agent: {result.get('routed_to_agent', False)}")
    print(f"{'='*60}")


def parse_args():
    parser = argparse.ArgumentParser(description="Test GE streamAssist API")
    parser.add_argument("--de-location", default=DE_LOCATION,
                        help="Discovery Engine location: 'global' or 'us' (default: global)")
    parser.add_argument("--ge-engine", default=GE_ENGINE,
                        help="GE engine ID")
    parser.add_argument("--ge-agent", default=GE_AGENT_ID,
                        help="GE agent ID (the one mapped to reasoning engine)")
    parser.add_argument("--ae-engine", default=AE_ENGINE_ID,
                        help="Agent Engine (reasoning engine) ID")
    parser.add_argument("--project-number", default=PROJECT_NUMBER,
                        help="GCP project number")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    DE_LOCATION = args.de_location
    GE_ENGINE = args.ge_engine
    GE_AGENT_ID = args.ge_agent
    AE_ENGINE_ID = args.ae_engine
    PROJECT_NUMBER = args.project_number
    main()
