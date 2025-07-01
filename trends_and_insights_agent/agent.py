from google.genai import types
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import load_artifacts

from .common_agents.campaign_guide_data_generation.agent import (
    campaign_guide_data_generation_agent,
    campaign_guide_data_extract_agent,
)
from .common_agents.report_generator.agent import (
    report_generator_agent,
)
# from .common_agents.yt_researcher.agent import yt_researcher_agent
# from .common_agents.gs_researcher.agent import gs_researcher_agent
# from .common_agents.campaign_researcher.agent import campaign_researcher_agent
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .common_agents.staged_researcher.agent import stage_1_research_merger

from .shared_libraries import callbacks
from .utils import MODEL
from .tools import get_user_file, load_sample_guide
from .prompts import (
    GLOBAL_INSTR,
    AUTO_ROOT_AGENT_INSTR,
    v2_ROOT_AGENT_INSTR,
)


root_agent = Agent(
    model=MODEL,
    name="root_agent",
    description="A trend and insight assistant using the services of multiple sub-agents.",
    instruction=v2_ROOT_AGENT_INSTR, #AUTO_ROOT_AGENT_INSTR,
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        campaign_guide_data_generation_agent,
        trends_and_insights_agent,
        ad_content_generator_agent,
        report_generator_agent,
        # campaign_researcher_agent,
        # yt_researcher_agent,
        # gs_researcher_agent,
        stage_1_research_merger,
    ],
    tools=[
        # load_artifacts,
        # call_campaign_guide_agent,
        # get_user_file,
        # load_sample_guide,
        # AgentTool(agent=campaign_guide_data_extract_agent),
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks.campaign_callback_function,
        # callbacks.before_agent_get_user_file,
    ],
    # after_agent_callback=callbacks.campaign_callback_function,
)
