import os
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import preload_memory

from .skills.trend_discovery.agents import trends_and_insights_agent
from .skills.market_research.agents import research_orchestrator
from .skills.ad_creative.agents import ad_content_generator_agent
from .skills.ad_creative.tools import save_creatives_and_research_report
from .skills.av_studio.agents import av_editing_studio_agent

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import (
    GLOBAL_INSTR,
    ROOT_AGENT_INSTR,
)
from google.adk.planners import BuiltInPlanner

root_agent = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant using the services of multiple sub-agents.",
    instruction=ROOT_AGENT_INSTR,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    ),
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        research_orchestrator,
        trends_and_insights_agent,
        ad_content_generator_agent,
        av_editing_studio_agent,
    ],
    tools=[save_creatives_and_research_report, preload_memory],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks._load_session_state,
        callbacks.campaign_callback_function,
    ],
    before_model_callback=callbacks.rate_limit_callback,
)
