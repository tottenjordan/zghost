from google.genai import types
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import load_artifacts

from .common_agents.campaign_guide_data_generation.agent import (
    campaign_guide_data_generation_agent,
)
from .common_agents.report_generator.agent import (
    report_generator_agent,
)
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .common_agents.staged_researcher.agent import stage_1_research_merger

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .tools import get_user_file, load_sample_guide
from .prompts import (
    GLOBAL_INSTR,
    AUTO_ROOT_AGENT_INSTR,
    v2_ROOT_AGENT_INSTR,
)


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
        stage_1_research_merger,
    ],
    tools=[
        # load_artifacts,
        # get_user_file,
        # load_sample_guide,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks._load_session_state,
        # callbacks.campaign_callback_function,
        # callbacks.before_agent_get_user_file,
    ],
)
