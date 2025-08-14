"""Standalone Research Orchestrator Agent for A2A Server.

This is a standalone version that doesn't conflict with the main agent hierarchy.
"""

import datetime
import logging
from typing import Any, Dict

from google.genai import types
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.tools import google_search, AgentTool
from google.adk.planners import BuiltInPlanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# We'll create a minimal standalone version for a2a
standalone_research_orchestrator = Agent(
    model="gemini-2.5-flash-latest",
    name="research_orchestrator",
    description="Orchestrates comprehensive research across multiple sources and generates unified insights.",
    instruction="""You are the Research Orchestrator agent responsible for coordinating comprehensive research.
    
    Your responsibilities:
    1. Coordinate parallel research across YouTube trends, Google Search trends, and campaign materials
    2. Evaluate the quality and completeness of research findings
    3. Execute follow-up searches to fill any gaps
    4. Synthesize all findings into a comprehensive, well-cited report
    
    Process the input data and return consolidated research insights.
    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
)