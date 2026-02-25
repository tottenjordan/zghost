import logging
import pathlib

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools.skill_toolset import SkillToolset

from .tools import (
    memorize,
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
)
from .prompts import AUTO_TREND_AGENT_INSTR
from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from ...skills.skill_loader import load_skill_from_dir
from google.adk.planners import BuiltInPlanner

# Load this skill's own SKILL.md for self-contained documentation
_skill_dir = pathlib.Path(__file__).parent
_skill = load_skill_from_dir(_skill_dir)
_skill_toolset = SkillToolset(skills=[_skill])

trends_and_insights_agent = Agent(
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
        _skill_toolset,
    ],
    before_agent_callback=callbacks._load_session_state,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_level="LOW",
        )
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
