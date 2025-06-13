from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import LongRunningFunctionTool

# from google.adk.tools import google_search

from ...prompts import global_instructions
from ...utils import MODEL
from ...tools import (
    query_web,
    query_youtube_api,
    analyze_youtube_videos,
    call_insights_generation_agent,
    call_yt_trends_generator_agent,
    call_search_trends_generator_agent,
)
from .prompts import AUTO_UNIFIED_RESEARCH_PROMPT  # , unified_web_research_prompt


tools = [
    query_web,
    query_youtube_api,
    LongRunningFunctionTool(analyze_youtube_videos),
    call_insights_generation_agent,
    call_yt_trends_generator_agent,
    call_search_trends_generator_agent,
]
web_researcher_agent = Agent(
    model=MODEL,
    name="web_researcher_agent",
    instruction=AUTO_UNIFIED_RESEARCH_PROMPT,  # unified_web_research_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
