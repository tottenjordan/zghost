from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import load_artifacts

from .common_agents.marketing_guide_data_generator.agent import (
    campaign_guide_data_generation_agent,
)
from .common_agents.report_generator.agent import (
    report_generator_agent,
)
from .common_agents.web_researcher.agent import web_researcher_agent
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .tools import call_campaign_guide_agent
from .utils import campaign_callback_function, MODEL
from .prompts import (
    global_instructions,
    AUTO_ROOT_AGENT_INSTR,
)


root_agent = Agent(
    model=MODEL,
    name="marketing_idea_generator_agent",
    instruction=AUTO_ROOT_AGENT_INSTR,
    global_instruction=global_instructions,
    sub_agents=[
        # campaign_guide_data_generation_agent,
        trends_and_insights_agent,
        web_researcher_agent,
        ad_content_generator_agent,
        report_generator_agent,
    ],
    tools=[
        # load_artifacts,
        call_campaign_guide_agent
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    after_agent_callback=campaign_callback_function,
)
