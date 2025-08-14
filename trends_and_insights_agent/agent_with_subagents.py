"""Root Agent with Sub-Agent Integration.

This version uses direct sub-agent integration for a2a-style architecture
without requiring external a2a servers.
"""

import logging
from typing import Dict, Any

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import load_artifacts, transfer_to_agent

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import GLOBAL_INSTR, ROOT_AGENT_INSTR

# Import the original sub-agents directly
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.staged_researcher.agent import research_orchestrator
from .common_agents.ad_content_generator.agent import ad_content_generator_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Enhanced root agent instruction for sub-agent coordination
ENHANCED_ROOT_INSTRUCTION = f"""{ROOT_AGENT_INSTR}

You coordinate with three specialized sub-agents using the transfer_to_agent tool:

1. **trends_insights**: Handles trend selection and campaign data extraction
   - Transfer when: User uploads PDFs or requests trend analysis
   - Returns: target trends, campaign data, initial insights

2. **research_orchestrator**: Performs comprehensive multi-source research  
   - Transfer when: After trends are selected and campaign data is extracted
   - Returns: consolidated research report with citations

3. **ad_generator**: Creates comprehensive ad campaigns with media
   - Transfer when: After research is complete
   - Returns: ad copy, visual concepts, generated images/videos

Workflow:
1. Start with greeting and guide user through PDF upload and trend selection
2. Transfer to trends_insights agent for data extraction and trend analysis
3. Transfer to research_orchestrator for comprehensive research
4. Transfer to ad_generator for creative campaign generation
5. Compile and present final report with all assets

Use the session state to maintain context between agent transfers.
Always be explicit about which agent you're transferring to and why.
"""


# Root agent with direct sub-agent integration
root_agent_with_subagents = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant orchestrating multiple specialized sub-agents.",
    instruction=ENHANCED_ROOT_INSTRUCTION,
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        trends_and_insights_agent,
        research_orchestrator,
        ad_content_generator_agent,
    ],
    tools=[
        transfer_to_agent,
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks._load_session_state,
        callbacks.before_agent_get_user_file,
    ],
    before_model_callback=callbacks.rate_limit_callback,
)