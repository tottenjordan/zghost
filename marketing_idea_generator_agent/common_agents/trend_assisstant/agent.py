from .prompts import unified_trends_instructions
from google.genai import types
from google.adk.agents import Agent

# from google.adk.tools import google_search

from ...tools import query_youtube_api, query_web, analyze_youtube_videos
from .tools import get_youtube_trends, call_trends_generator_agent
from google.adk.tools import LongRunningFunctionTool


# official_tooling = [google_search]
tools = [
    get_youtube_trends,
    query_youtube_api,
    query_web,
    LongRunningFunctionTool(analyze_youtube_videos),
    call_trends_generator_agent,
]

trends_and_insights_agent = Agent(
    model="gemini-2.0-flash-001",
    name="trends_and_insights_agent",
    instruction=unified_trends_instructions,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
