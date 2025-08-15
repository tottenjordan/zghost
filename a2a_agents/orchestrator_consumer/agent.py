"""A2A Orchestrator Consumer Agent.

This agent consumes the three A2A server agents (trends_insights, research_orchestrator, 
and ad_generator) to provide a complete marketing intelligence workflow.
"""

import os
import logging
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config
from .config import config

# Configuration for A2A server locations
A2A_HOST = os.getenv("A2A_HOST", "localhost")
TRENDS_PORT = os.getenv("TRENDS_INSIGHTS_PORT", "9001")
RESEARCH_PORT = os.getenv("RESEARCH_ORCHESTRATOR_PORT", "9000")
AD_GEN_PORT = os.getenv("AD_GENERATOR_PORT", "9002")

# Create RemoteA2aAgent instances for each server
trends_insights_agent = RemoteA2aAgent(
    name="trends_insights_agent",
    description="Agent that handles trend selection, PDF campaign guide extraction, and initial insights generation.",
    agent_card=(
        f"http://{A2A_HOST}:{TRENDS_PORT}/a2a/trends_insights{AGENT_CARD_WELL_KNOWN_PATH}"
    ),
)

research_orchestrator_agent = RemoteA2aAgent(
    name="research_orchestrator_agent",
    description="Agent that orchestrates comprehensive research across multiple sources and generates unified insights.",
    agent_card=(
        f"http://{A2A_HOST}:{RESEARCH_PORT}/research_orchestrator{AGENT_CARD_WELL_KNOWN_PATH}"
    ),
)

ad_generator_agent = RemoteA2aAgent(
    name="ad_generator_agent",
    description="Agent that generates comprehensive ad campaigns with copy, visuals, and media assets.",
    agent_card=(
        f"http://{A2A_HOST}:{AD_GEN_PORT}/ad_generator{AGENT_CARD_WELL_KNOWN_PATH}"
    ),
)

# Main orchestrator instruction
ORCHESTRATOR_INSTRUCTION = """You are a marketing intelligence orchestrator that coordinates three specialized A2A agents:

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

## Workflow:
1. Start with a friendly greeting and guide user through PDF upload and trend selection using trends_insights_agent
2. Extract campaign data and gather trend selections
3. Pass extracted data to research_orchestrator_agent for comprehensive research
4. Use research results with ad_generator_agent to create ad campaigns
5. Compile and present final report with all assets

## Important Guidelines:
- Always maintain conversation context and flow naturally between agent invocations
- Extract and preserve important data from each agent's response in session state
- Handle errors gracefully and inform the user if an agent is unavailable
- Present results in a clear, structured format with all generated assets

## Session State Management:
You must track and maintain the following data throughout the session:
- target_search_trends: Selected Google Search trends
- target_yt_trends: Selected YouTube trends
- target_product: Product being marketed
- target_audience: Target audience
- campaign_guide_data: Extracted campaign information
- draft_report: Research findings
- generated_assets: Images, videos, and copy created

Remember: You are the orchestrator providing a seamless experience by coordinating these specialized agents."""

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
        trends_insights_agent,
        research_orchestrator_agent,
        ad_generator_agent,
    ],
    tools=[
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
)