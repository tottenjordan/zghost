from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import load_artifacts

from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.staged_researcher.agent import research_orchestrator
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .common_agents.ad_content_generator.tools import save_creatives_and_research_report

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import (
    GLOBAL_INSTR,
    ROOT_AGENT_INSTR,
)

root_agent = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant using the services of multiple sub-agents.",
    instruction=ROOT_AGENT_INSTR,
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        research_orchestrator,
        trends_and_insights_agent,
        ad_content_generator_agent,
    ],
    tools=[save_creatives_and_research_report, load_artifacts],
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
