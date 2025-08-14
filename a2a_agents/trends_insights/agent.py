"""Trends and Insights A2A Server Agent.

This agent handles trend selection, data extraction from campaign guides,
and initial insights generation.
"""

import logging
from typing import Any, Dict

from google.genai import types
from google.adk.agents import Agent
from typing import List, Optional
from pydantic import BaseModel, Field

from trends_and_insights_agent.common_agents.trend_assistant.agent import (
    trends_and_insights_agent as original_trends_agent,
)
from trends_and_insights_agent.shared_libraries import callbacks
from trends_and_insights_agent.shared_libraries.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Use the existing trends and insights agent as the base
trends_insights_agent = original_trends_agent


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
    name="trends_insights",
    description="Handles trend selection, campaign guide data extraction, and initial insights generation.",
    capabilities=[
        "Google Search trend analysis",
        "YouTube trend analysis",
        "PDF campaign guide extraction",
        "YouTube video summarization",
        "Initial insights generation",
        "Interactive trend selection",
    ],
    input_schema={
        "type": "object",
        "properties": {
            "user_message": {
                "type": "string",
                "description": "User's message or request",
            },
            "uploaded_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of uploaded file paths (PDFs)",
                "required": False,
            },
            "selected_trend": {
                "type": "string",
                "description": "User's selected trend",
                "required": False,
            },
        },
        "required": ["user_message"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "target_search_trends": {
                "type": "object",
                "description": "Selected Google Search trends",
            },
            "target_yt_trends": {
                "type": "object",
                "description": "Selected YouTube trends",
            },
            "yt_video_analysis": {
                "type": "string",
                "description": "YouTube video summary and analysis",
            },
            "campaign_guide_data": {
                "type": "object",
                "description": "Extracted campaign guide information",
            },
            "target_product": {
                "type": "string",
                "description": "Identified product from campaign guide",
            },
            "target_audience": {
                "type": "string",
                "description": "Identified target audience",
            },
            "available_trends": {
                "type": "array",
                "description": "List of available trends for selection",
                "required": False,
            },
        },
    },
    version="1.0.0",
    author="ZGhost Team",
    license="Apache-2.0",
)