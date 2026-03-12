"""Configuration for deployment to Agent Engine and Gemini Enterprise."""

import os
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeployConfig:
    """Deployment configuration resolved from env vars or deployment_info.json."""

    project_id: str = ""
    project_number: str = ""
    agent_engine_location: str = "us-central1"
    agentspace_location: str = "global"
    agentspace_app_id: str = "gemini-enterprise-17634901_1763490144996"
    reasoning_engine_id: str = ""
    display_name: str = "ralph-wiggum"
    description: str = "AI assistant for web research and ad creative generation."
    instructions: str = "Use this agent for marketing research, trend analysis, and ad creative generation."
    icon_uri: str = "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"

    @classmethod
    def from_env(cls) -> "DeployConfig":
        """Load config from environment variables."""
        from dotenv import load_dotenv
        load_dotenv("trends_and_insights_agent/.env")
        return cls(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            project_number=os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER", ""),
            agent_engine_location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            agentspace_location=os.getenv("AGENTSPACE_LOCATION", "us"),
            agentspace_app_id=os.getenv("AGENTSPACE_APP_ID", ""),
        )

    @classmethod
    def from_deployment_info(cls, path: str = "deployment_info.json") -> "DeployConfig":
        """Load config from deployment_info.json, merging with env vars."""
        config = cls.from_env()
        if os.path.exists(path):
            with open(path) as f:
                info = json.load(f)
            config.reasoning_engine_id = info.get("engine_id", config.reasoning_engine_id)
            if not config.project_number and info.get("project_number"):
                config.project_number = info["project_number"]
        return config
