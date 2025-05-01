# from typing import Optional
from google.genai import types

from google.adk.agents import Agent

# from google.adk.models import LlmRequest
from google.adk.tools import load_artifacts

# from google.adk.tools import google_search
# from google.adk.agents.callback_context import CallbackContext
# from google.adk.tools.google_search_tool import GoogleSearchTool

from .common_agents.marketing_guide_data_generator.agent import (
    campaign_guide_data_generation_agent,
)
from .common_agents.research_generator.agent import (
    research_generation_agent,
)
from .common_agents.web_researcher.agent import web_researcher_agent
from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .prompts import root_agent_instructions

# from .tools import call_guide_generation_agent
from .utils import campaign_callback_function


root_agent = Agent(
    model="gemini-2.0-flash-001",
    name="marketing_idea_generator_agent",
    instruction=root_agent_instructions,
    global_instruction=(
        f"""
        You are an expert marketing agent developing research-based marketing campaign briefs, enriched by Google Search and YouTube.
        """
    ),
    sub_agents=[
        web_researcher_agent,  # research on the web and Youtube
        ad_content_generator_agent,  # create content from imagen and veo
        trends_and_insights_agent,  # get broad trends from Youtube
        campaign_guide_data_generation_agent,  # creates structured data from campaign documents
        research_generation_agent,  # generates a final research brief
    ],
    tools=[
        # google_search,
        load_artifacts,
        # call_guide_generation_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    after_agent_callback=campaign_callback_function,
)
