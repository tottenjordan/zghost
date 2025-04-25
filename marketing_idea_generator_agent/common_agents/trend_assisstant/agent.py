from .prompts import (
    get_youtube_trends_prompt,
)
from google.genai import types
from google.adk.agents import Agent
# from google.adk.tools import google_search

from ...tools import (
    query_youtube_api, 
    query_web, 
    analyze_youtube_videos
)
from .tools import get_youtube_trends
from google.adk.tools import LongRunningFunctionTool


# official_tooling = [google_search]
tools = [
    get_youtube_trends,
    query_youtube_api,
    query_web,
    LongRunningFunctionTool(analyze_youtube_videos),
]

trends_and_insights_agent = Agent(
    model="gemini-2.0-flash-001",
    name="trends_and_insights_agent",
    instruction=get_youtube_trends_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
