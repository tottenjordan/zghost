from google.genai import types
from google.adk.agents import Agent

# from google.adk.tools import load_artifacts

from .common_agents.report_generator.agent import report_generator_agent
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.staged_researcher.agent import combined_research_merger
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .common_agents.campaign_guide_data_generation.agent import (
    campaign_guide_data_generation_agent,
)

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import (
    GLOBAL_INSTR,
    v2_ROOT_AGENT_INSTR,
)

# TODO: system generated prompt says: "You are an agent. Your internal name is 'trends_and_insights_agent'."
root_agent = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant using the services of multiple sub-agents.",
    instruction=v2_ROOT_AGENT_INSTR,
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        campaign_guide_data_generation_agent,
        trends_and_insights_agent,
        ad_content_generator_agent,
        report_generator_agent,
        combined_research_merger,
    ],
    # tools=[
    #     load_artifacts,
    # ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks._load_session_state,
    ],
    before_model_callback=callbacks.rate_limit_callback,
)
