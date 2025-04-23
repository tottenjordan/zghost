from .prompts import (
    create_brief_prompt,
    youtube_url_instructions,
)
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import LongRunningFunctionTool

from google.adk.tools import google_search
from ...tools import query_youtube_api, query_web, analyze_youtube_videos


official_tooling = [google_search]
tools = [
    LongRunningFunctionTool(analyze_youtube_videos),
    query_youtube_api,
    LongRunningFunctionTool(query_web),
]
create_new_ideas_agent = Agent(
    model="gemini-2.0-flash",
    name="create_new_ideas_agent",
    instruction=create_brief_prompt + youtube_url_instructions,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
