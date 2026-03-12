#!/usr/bin/env python3
"""Register, list, or delete an ADK agent in Gemini Enterprise (Discovery Engine).

Usage:
    python -m deploy.register_gemini_enterprise register [--from-deployment-info]
    python -m deploy.register_gemini_enterprise list
    python -m deploy.register_gemini_enterprise delete --agent-id <ID>
"""

import argparse
import json
import logging
import sys

import google.auth
import google.auth.transport.requests

from .config import DeployConfig

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _get_access_token() -> str:
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _base_url(config: DeployConfig) -> str:
    return (
        f"https://{config.agentspace_location}-discoveryengine.googleapis.com/v1alpha"
        f"/projects/{config.project_number}"
        f"/locations/{config.agentspace_location}"
        f"/collections/default_collection"
        f"/engines/{config.agentspace_app_id}"
        f"/assistants/default_assistant/agents"
    )


def _headers(config: DeployConfig, token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": config.project_id,
    }


def _reasoning_engine_path(config: DeployConfig) -> str:
    return (
        f"projects/{config.project_number}"
        f"/locations/{config.agent_engine_location}"
        f"/reasoningEngines/{config.reasoning_engine_id}"
    )


def list_agents(config: DeployConfig) -> list:
    """List all agents registered in Gemini Enterprise."""
    import requests

    token = _get_access_token()
    resp = requests.get(_base_url(config), headers=_headers(config, token))
    resp.raise_for_status()
    data = resp.json()
    agents = data.get("agents", [])
    for agent in agents:
        log.info(
            f"  Agent: {agent.get('displayName', 'N/A')} "
            f"(ID: {agent.get('name', '').split('/')[-1]})"
        )
    if not agents:
        log.info("  No agents found.")
    return agents


def register_agent(config: DeployConfig) -> dict:
    """Register (create) an agent in Gemini Enterprise. Idempotent: skips if exists."""
    import requests

    # Check if already registered
    existing = list_agents(config)
    for agent in existing:
        if agent.get("displayName") == config.display_name:
            log.info(f"Agent '{config.display_name}' already registered. Skipping.")
            return agent

    token = _get_access_token()
    body = {
        "displayName": config.display_name,
        "description": config.description,
        "icon": {"uri": config.icon_uri},
        "adk_agent_definition": {
            "tool_settings": {
                "tool_description": config.instructions,
            },
            "provisioned_reasoning_engine": {
                "reasoning_engine": _reasoning_engine_path(config),
            },
        },
    }

    log.info(f"Registering agent '{config.display_name}' with Gemini Enterprise...")
    log.info(f"  Reasoning Engine: {_reasoning_engine_path(config)}")
    resp = requests.post(
        _base_url(config),
        headers=_headers(config, token),
        json=body,
    )
    resp.raise_for_status()
    result = resp.json()
    agent_id = result.get("name", "").split("/")[-1]
    log.info(f"  Registered successfully! Agent ID: {agent_id}")
    return result


def delete_agent(config: DeployConfig, agent_id: str) -> None:
    """Delete an agent from Gemini Enterprise."""
    import requests

    token = _get_access_token()
    url = f"{_base_url(config)}/{agent_id}"
    log.info(f"Deleting agent {agent_id}...")
    resp = requests.delete(url, headers=_headers(config, token))
    resp.raise_for_status()
    log.info("  Deleted successfully.")


def main():
    parser = argparse.ArgumentParser(description="Manage agents in Gemini Enterprise")
    parser.add_argument("action", choices=["register", "list", "delete"])
    parser.add_argument("--agent-id", help="Agent ID (required for delete)")
    parser.add_argument(
        "--from-deployment-info",
        action="store_true",
        help="Read engine ID from deployment_info.json",
    )
    parser.add_argument("--reasoning-engine-id", help="Override reasoning engine ID")
    parser.add_argument("--app-id", help="Override Agentspace app ID")
    args = parser.parse_args()

    if args.from_deployment_info:
        config = DeployConfig.from_deployment_info()
    else:
        config = DeployConfig.from_env()

    if args.reasoning_engine_id:
        config.reasoning_engine_id = args.reasoning_engine_id
    if args.app_id:
        config.agentspace_app_id = args.app_id

    if args.action == "list":
        list_agents(config)
    elif args.action == "register":
        if not config.reasoning_engine_id:
            log.error("reasoning_engine_id is required. Use --reasoning-engine-id or --from-deployment-info")
            sys.exit(1)
        if not config.agentspace_app_id:
            log.error("agentspace_app_id is required. Use --app-id or set AGENTSPACE_APP_ID env var")
            sys.exit(1)
        register_agent(config)
    elif args.action == "delete":
        if not args.agent_id:
            log.error("--agent-id is required for delete")
            sys.exit(1)
        delete_agent(config, args.agent_id)


if __name__ == "__main__":
    main()
