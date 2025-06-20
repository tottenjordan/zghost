from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import load_artifacts

from .common_agents.marketing_guide_data_generator.agent import (
    campaign_guide_data_generation_agent,
)
from .common_agents.report_generator.agent import (
    report_generator_agent,
)
from .common_agents.yt_researcher.agent import yt_researcher_agent
from .common_agents.gs_researcher.agent import gs_researcher_agent
from .common_agents.campaign_researcher.agent import campaign_researcher_agent
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.ad_content_generator.agent import ad_content_generator_agent

from .shared_libraries import callbacks
from .tools import call_campaign_guide_agent
from .utils import MODEL
from .prompts import (
    GLOBAL_INSTR,
    AUTO_ROOT_AGENT_INSTR,
)


root_agent = Agent(
    model=MODEL,
    name="marketing_idea_generator_agent",
    description="A trend and insight assistant using the services of multiple sub-agents",
    instruction=AUTO_ROOT_AGENT_INSTR,
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        campaign_guide_data_generation_agent,
        trends_and_insights_agent,
        ad_content_generator_agent,
        report_generator_agent,
        campaign_researcher_agent,
        yt_researcher_agent,
        gs_researcher_agent,
    ],
    tools=[
        # load_artifacts,
        # call_campaign_guide_agent
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    after_agent_callback=callbacks.campaign_callback_function,
)
