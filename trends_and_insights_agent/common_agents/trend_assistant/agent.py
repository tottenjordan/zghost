from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import LongRunningFunctionTool

from .tools import (
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
)
from .prompts import AUTO_TREND_AGENT_INSTR
from ...utils import MODEL

# from ...prompts import GLOBAL_INSTR

tools = [
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
]

trends_and_insights_agent = Agent(
    model=MODEL,
    name="trends_and_insights_agent",
    description="Displays trends from Search and YouTube to the user and captures their selection(s).",
    instruction=AUTO_TREND_AGENT_INSTR,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    # after_tool_callback=save_yt_trends_to_session_state,
)
