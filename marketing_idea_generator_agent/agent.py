from google.genai import types

from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from .common_agents.marketing_brief_data_generator.agent import (
    brief_data_generation_agent,
)
from .common_agents.idea_generator.agent import create_new_ideas_agent
from .prompts import root_agent_instructions

# from google.adk.tools.google_search_tool import GoogleSearchTool
from .common_agents.image_generator.agent import image_generation_agent
from google.adk.tools import google_search

from .common_agents.trend_assisstant.agent import trends_and_insights_agent
from .tools import call_brief_generation_agent

root_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="marketing_idea_generator_agent",
    instruction=root_agent_instructions,
    global_instruction=(
        f"""
        You are an expert marketing agent developing research-based marketing campaign briefs, enriched by Google Search and YouTube.
        """
    ),
    sub_agents=[
        # brief_data_generation_agent,
        create_new_ideas_agent,
        image_generation_agent,
        trends_and_insights_agent,
    ],
    tools=[
        # google_search,
        load_artifacts,
        call_brief_generation_agent
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01, 
        # response_modalities=["TEXT", "AUDIO"]
    ),
)
