from .prompts import (
    get_youtube_trends_prompt,
)
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search
from .tools import (
    get_youtube_trends,
    search_yt,
)

official_tooling = [google_search]
tools = [get_youtube_trends, search_yt]

trends_and_insights_agent = Agent(
    model="gemini-2.0-flash-001",
    name="trends_and_insights_agent",
    instruction=get_youtube_trends_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)