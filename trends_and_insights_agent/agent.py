from google.genai import types

from google.adk.agents import Agent

from google.adk.tools import load_artifacts


from .common_agents.marketing_guide_data_generator.agent import (
    campaign_guide_data_generation_agent,
)
from .common_agents.research_generator.agent import (
    research_generation_agent,
)
from .common_agents.web_researcher.agent import web_researcher_agent
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .prompts import root_agent_instructions, global_instructions

from .utils import campaign_callback_function, MODEL


root_agent = Agent(
    model=MODEL,
    name="marketing_idea_generator_agent",
    instruction=root_agent_instructions,
    global_instruction=global_instructions,
    sub_agents=[
        web_researcher_agent,  # research on the web and Youtube
        ad_content_generator_agent,  # create content from imagen and veo
        trends_and_insights_agent,  # get broad trends from Youtube
        campaign_guide_data_generation_agent,  # creates structured data from campaign documents
        research_generation_agent,  # generates a final research brief
    ],
    tools=[
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    after_agent_callback=campaign_callback_function,
)
