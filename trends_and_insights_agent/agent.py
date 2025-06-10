from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import load_artifacts

from .common_agents.marketing_guide_data_generator.agent import (
    campaign_guide_data_generation_agent,
)
from .common_agents.report_generator.agent import (
    report_generator_agent,  # research_generation_agent,
)
from .common_agents.web_researcher.agent import web_researcher_agent
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .prompts import root_agent_instructions, global_instructions
from .tools import call_campaign_guide_agent
from .utils import campaign_callback_function, MODEL


root_agent = Agent(
    model=MODEL,
    name="marketing_idea_generator_agent",
    instruction=root_agent_instructions,
    global_instruction=global_instructions,
    sub_agents=[
        web_researcher_agent,  # research on the web and YouTube
        ad_content_generator_agent,  # create content from imagen and veo
        trends_and_insights_agent,  # extract trending topics from search and trending content from youtube; generate insights
        campaign_guide_data_generation_agent,  # creates structured data from campaign documents
        report_generator_agent,  # generates a final research brief report
    ],
    tools=[
        load_artifacts,
        # call_campaign_guide_agent
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    after_agent_callback=campaign_callback_function,
)
