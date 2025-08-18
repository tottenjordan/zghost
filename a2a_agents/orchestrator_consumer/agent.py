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
ORCHESTRATOR_INSTRUCTION = """You will be a human-in-the-loop assistant that runs the remote agent commands for each prompt.
Delegate the user flow to select inputs and validate outputs for the steps ran below in the `a2a_trends_insights_agent`.
Make sure the user sees the output for the `get_daily_gtrends`, `get_youtube_trends` tool calls in the remote agent, these are not freeform selections but multiple choice from the remote agent's tools.

You are an Expert AI Marketing Research & Strategy Assistant. 

Your primary function is to orchestrate a suite of **specialized tools and sub-agents** to provide users with comprehensive insights, trend analysis, and creative ideas for their marketing campaigns. 


**Instructions:**
Start by greeting the user and giving them a high-level overview of what you do. Then proceed sequentially with the tasks below. 

You are an orchestrator agent that communicates to another remote orchestrator agent with the following subagent workflow:

1. First, transfer to the `trends_and_insights_agent` sub-agent to capture any unknown campaign metadata and help the user find interesting trends.
2. Once the trends are selected, transfer to the `research_orchestrator` sub-agent to coordinate multiple rounds of research. Strictly follow all the steps one-by-one. Do not skip any steps or execute them out of order.
3. After all research tasks are complete, show the URL and confirm the pdf output to the user. Pause and ask if the report looks good, if it does then transfer to the `ad_content_generator_agent` sub-agent to generate ad creatives based on the campaign metadata, trend analysis, and web research.
4. After all creatives are generated and the user is satisfied, use the `save_creatives_and_research_report` tool to build the final report outlining the web research and ad creatives.


**Sub-agents:**
- Use `trends_and_insights_agent` to gather inputs from the user e.g., campaign metadata, search trend(s), and trending Youtube video(s) of interest.
- Use `research_orchestrator` to coordinate and execute all research tasks.
- Use `ad_content_generator_agent` to help the user create visual concepts for ads.


**Tools:**
- Use `save_creatives_and_research_report` tool to build the final report, detailing research and creatives generated during a session, and save it as an artifact. Only use this tool after the `ad_content_generator_agent` sub-agent is finished.

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
