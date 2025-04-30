from .prompts import unified_insights_prompt
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import LongRunningFunctionTool

# from google.adk.tools import google_search
from ...tools import (
    call_insights_generation_agent,
    query_youtube_api,
    query_web,
    analyze_youtube_videos,
)

# official_tooling = [google_search]
tools = [
    LongRunningFunctionTool(analyze_youtube_videos),
    query_youtube_api,
    query_web,
    call_insights_generation_agent,
]
create_new_ideas_agent = Agent(
    model="gemini-2.0-flash-001",
    name="create_new_ideas_agent",
    instruction=unified_insights_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
