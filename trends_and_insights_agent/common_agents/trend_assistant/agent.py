"""
Seperating duties for "trending content" vs "trending search topics":
> Search Trends provide insights into what the world is searching for
> YouTube Trends showcase videos that are broadly interesting and capture what's happening on YouTube and in the world
> YouTube trends are about engagement with video content, while Google Search trends are about search behavior
"""

from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import LongRunningFunctionTool

from ...prompts import global_instructions
from ...utils import MODEL

# from ...tools import (
#     query_youtube_api,
#     query_web,
#     analyze_youtube_videos,
# )

from .tools import (
    get_daily_gtrends,
    get_youtube_trends,
    call_target_yt_trend_agent,
    call_target_search_trend_agent,
)
from .prompts import unified_target_trend_instructions


tools = [
    get_daily_gtrends,
    get_youtube_trends,
    call_target_yt_trend_agent,
    call_target_search_trend_agent,
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


# trend_liason_agent = Agent(
#     model=MODEL,
#     name="trend_liason_agent",
#     global_instruction=global_instructions,
#     instruction=get_user_selected_trends_instructions,
#     tools=[
#         get_daily_gtrends,
#         get_youtube_trends,
#         call_target_yt_trend_agent,
#         call_target_search_trend_agent,
#     ],
#     generate_content_config=types.GenerateContentConfig(
#         temperature=1.0,
#     ),
#     # output_key="search_trends"
# )


# search_trends_agent = Agent(
#     model=MODEL,
#     name="search_trends_agent",
#     global_instruction=global_instructions,
#     instruction=unified_search_trends_instructions,
#     tools=[
#         get_daily_gtrends,
#         query_web,
#         call_search_trends_generator_agent,
#     ],
#     generate_content_config=types.GenerateContentConfig(
#         temperature=1.0,
#     ),
#     # output_key="search_trends"
# )


# yt_trends_agent = Agent(
#     model=MODEL,
#     name="yt_trends_agent",
#     global_instruction=global_instructions,
#     instruction=unified_yt_trends_instructions,
#     tools=[
#         get_youtube_trends,
#         query_youtube_api,
#         query_web,
#         LongRunningFunctionTool(analyze_youtube_videos),
#         call_yt_trends_generator_agent,  # call_trends_generator_agent,
#     ],
#     generate_content_config=types.GenerateContentConfig(
#         temperature=1.0,
#     ),
#     # output_key="yt_trends"
# )


# trends_sequential_agent = SequentialAgent(
#     name="trends_sequential_agent",
#     description=(
#         "Gets trending topics from Search and generates insight from web research; "
#         "Gets trending content from YouTube, generates insights from video analysis and web research"
#     ),
#     sub_agents=[search_trends_agent, yt_trends_agent],
# )
