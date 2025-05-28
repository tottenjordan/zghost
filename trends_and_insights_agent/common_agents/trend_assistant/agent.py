"""
Separating duties for "trending content" vs "trending search topics":
> Search Trends provide insights into what the world is searching for
> YouTube Trends showcase videos that are broadly interesting and capture what's happening on YouTube and in the world
> YouTube trends are about engagement with video content, while Google Search trends are about search behavior
"""

from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import LongRunningFunctionTool

from ...prompts import global_instructions
from ...utils import MODEL

from .tools import (
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
)
from .prompts import unified_target_trend_instructions


tools = [
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
]

trends_and_insights_agent = Agent(
    model=MODEL,
    name="trends_and_insights_agent",
    global_instruction=global_instructions,
    instruction=unified_target_trend_instructions,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
