"""Research Orchestrator A2A Server Agent.

This agent coordinates parallel research across YouTube trends, Google Search trends,
and campaign materials, then synthesizes the results into comprehensive insights.
"""

import datetime
import logging
from typing import Any, Dict

from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search
from google.adk.planners import BuiltInPlanner
from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field

from trends_and_insights_agent.common_agents.staged_researcher.agent import (
    research_orchestrator as base_research_orchestrator,
)
from trends_and_insights_agent.common_agents.staged_researcher.tools import (
    save_draft_report_artifact,
)
from trends_and_insights_agent.shared_libraries import callbacks
from trends_and_insights_agent.shared_libraries.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the existing research orchestrator as the base
research_orchestrator_agent = base_research_orchestrator


# Define agent card schema for a2a protocol
class AgentCardSchema(BaseModel):
    """Schema for agent card metadata."""
    name: str
    description: str
    capabilities: List[str]
    input_schema: dict
    output_schema: dict
    version: str
    author: str
    license: str


# Create agent card for a2a protocol
AGENT_CARD = AgentCardSchema(
    name="research_orchestrator",
    description="Orchestrates comprehensive research across multiple sources and generates unified insights.",
    capabilities=[
        "Parallel research coordination",
        "YouTube trend analysis",
        "Google Search trend analysis",
        "Campaign material research",
        "Research quality evaluation",
        "Follow-up search execution",
        "Report synthesis with citations",
    ],
    input_schema={
        "type": "object",
        "properties": {
            "target_search_trends": {
                "type": "object",
                "description": "Google Search trends to research",
            },
            "target_yt_trends": {
                "type": "object",
                "description": "YouTube trends to research",
            },
            "target_product": {
                "type": "string",
                "description": "Product being marketed",
            },
            "target_audience": {
                "type": "string",
                "description": "Target audience for the campaign",
            },
            "campaign_guide_data": {
                "type": "object",
                "description": "Campaign guide information",
                "required": False,
            },
        },
        "required": ["target_search_trends", "target_yt_trends", "target_product", "target_audience"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "combined_web_search_insights": {
                "type": "string",
                "description": "Consolidated research findings",
            },
            "draft_report": {
                "type": "string",
                "description": "Final research report with citations",
            },
            "sources": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of cited sources",
            },
        },
    },
    version="1.0.0",
    author="ZGhost Team",
    license="Apache-2.0",
)