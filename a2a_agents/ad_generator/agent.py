"""Ad Content Generator A2A Server Agent.

This agent generates comprehensive ad campaigns including copy, visual concepts,
and actual image/video generation using Imagen and Veo models.
"""

import logging
from typing import Any, Dict

from google.genai import types
from google.adk.agents import Agent
from typing import List, Optional
from pydantic import BaseModel, Field

from trends_and_insights_agent.common_agents.ad_content_generator.agent import (
    ad_content_generator_agent as original_ad_generator,
)
from trends_and_insights_agent.shared_libraries import callbacks
from trends_and_insights_agent.shared_libraries.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Use the existing ad content generator agent as the base
ad_generator_agent = original_ad_generator


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
    name="ad_generator",
    description="Generates comprehensive ad campaigns with copy, visuals, and media assets.",
    capabilities=[
        "Ad copy generation",
        "Creative critique and refinement",
        "Visual concept development",
        "Image generation with Imagen 4.0",
        "Video generation with Veo 2.0",
        "Creative package assembly",
        "Multi-format ad campaigns",
    ],
    input_schema={
        "type": "object",
        "properties": {
            "draft_report": {
                "type": "string",
                "description": "Research report with insights",
            },
            "target_product": {
                "type": "string",
                "description": "Product being marketed",
            },
            "target_audience": {
                "type": "string",
                "description": "Target audience",
            },
            "campaign_guide_data": {
                "type": "object",
                "description": "Campaign guide information",
            },
            "target_search_trends": {
                "type": "object",
                "description": "Google Search trends",
            },
            "target_yt_trends": {
                "type": "object",
                "description": "YouTube trends",
            },
            "creative_brief": {
                "type": "string",
                "description": "Optional creative brief or specific requirements",
                "required": False,
            },
        },
        "required": [
            "draft_report",
            "target_product",
            "target_audience",
            "campaign_guide_data",
            "target_search_trends",
            "target_yt_trends",
        ],
    },
    output_schema={
        "type": "object",
        "properties": {
            "ad_copy_variations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {"type": "string"},
                        "body": {"type": "string"},
                        "cta": {"type": "string"},
                        "format": {"type": "string"},
                    },
                },
                "description": "Multiple versions of ad copy",
            },
            "visual_concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "concept_name": {"type": "string"},
                        "description": {"type": "string"},
                        "mood": {"type": "string"},
                        "elements": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "description": "Detailed visual concept descriptions",
            },
            "generated_images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "URLs to generated images",
            },
            "generated_videos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "URLs to generated videos",
            },
            "creative_package": {
                "type": "object",
                "description": "Complete creative package with all assets",
            },
        },
    },
    version="1.0.0",
    author="ZGhost Team",
    license="Apache-2.0",
)