import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent

from .tools import (
    memorize,
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
)
from .prompts import AUTO_TREND_AGENT_INSTR
from .config import config
from .shared_libraries import callbacks


root_agent = Agent(
    model=config.worker_model,
    name="trends_and_insights_agent",
    description="Captures campaign metadata and displays trending topics from Google Search and trending videos from YouTube.",
    instruction=AUTO_TREND_AGENT_INSTR,
    tools=[
        memorize,
        get_daily_gtrends,
        get_youtube_trends,
        save_yt_trends_to_session_state,
        save_search_trends_to_session_state,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    before_agent_callback=[
        callbacks._load_session_state,
    ],
)
