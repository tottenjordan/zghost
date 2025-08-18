"""A2A Orchestrator Consumer Agent.

This agent consumes the three A2A server agents (trends_insights, research_orchestrator,
and ad_generator) to provide a complete marketing intelligence workflow.
"""

import os
import logging
from google.adk.agents.remote_a2a_agent import (
    RemoteA2aAgent,
    AGENT_CARD_WELL_KNOWN_PATH,
)
from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config
from .config import config

# Configuration for A2A server locations
A2A_HOST = os.getenv("A2A_HOST", "localhost")
A2A_PORT = os.getenv("A2A_PORT", "8100")

# Create RemoteA2aAgent instances for each server
a2a_trends_insights_agent = RemoteA2aAgent(
    name="trends_and_insights_agent",
    description="Agent that handles trend selection, PDF campaign guide extraction, and initial insights generation.",
    agent_card=(
        f"http://{A2A_HOST}:{A2A_PORT}/a2a/trends_and_insights_agent{AGENT_CARD_WELL_KNOWN_PATH}"
    ),
)

# Main orchestrator instruction
ORCHESTRATOR_INSTRUCTION = """You are a marketing intelligence orchestrator that coordinates three specialized A2A agents:

You will be a human-in-the-loop assistant as the remote agent goes through this workflow, which runs sequentially for each trend selection in the trends_and_insights_agent.
Delegate the user flow to select inputs and validate outputs for the steps ran below in the `a2a_trends_insights_agent`

1. **trends_insights_agent**: Handles trend selection and campaign data extraction
   - Use when: User uploads PDFs or requests trend analysis
   - Input: user_message, uploaded_files (optional), selected_trend (optional)
   - Returns: target trends, campaign data, initial insights

2. **research_orchestrator_agent**: Performs comprehensive multi-source research
   - Use when: After trends are selected and campaign data is extracted
   - Input: target_search_trends, target_yt_trends, target_product, target_audience, campaign_guide_data
   - Returns: consolidated research report with citations

3. **ad_generator_agent**: Creates comprehensive ad campaigns with media
   - Use when: After research is complete
   - Input: draft_report, target_product, target_audience, campaign_guide_data, trends, creative_brief
   - Returns: ad copy, visual concepts, generated images/videos
"""

# Global instruction
GLOBAL_INSTR = """Maintain a professional, helpful tone throughout all interactions.
Be concise but thorough in your responses.
Always prioritize user needs and provide clear guidance."""

# Create root_agent for a2a protocol
root_agent = Agent(
    model=config.worker_model,
    name="orchestrator_consumer",
    description="A marketing intelligence orchestrator that coordinates trend analysis, research, and ad generation through A2A agents.",
    instruction=ORCHESTRATOR_INSTRUCTION,
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        a2a_trends_insights_agent,
    ],
    tools=[
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    # before_agent_callback=[
    #     callbacks._load_session_state,
    # ],
)
