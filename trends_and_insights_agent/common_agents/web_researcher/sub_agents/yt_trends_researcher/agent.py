from google.genai import types
from google.adk.agents import Agent

# from google.adk.agents.llm_agent import LlmAgent
# from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import LongRunningFunctionTool

# from .....shared_libraries.types import json_response_config
from .....utils import MODEL, campaign_callback_function
from .....tools import (
    query_web,
    analyze_youtube_videos,
    call_yt_trends_generator_agent,
)


# Researcher 2: trending YouTube
_SEQ_YT_TREND_PROMPT = """**Role:** You are a Research Assistant specializing in YouTube trends.

**Objective:** Your goal is to conduct web research to gather insights related to the trending YouTube video(s). These insights should answer questions like:
*   What is the video about? what is being discussed? Who is involved?
*   Why is this video trending? 
*   Are there any themes that would resonate with our target audience(s)?

**Instructions:** Follow these steps to complete the task at hand:
1. For each entry in the `target_yt_trends` session state, use the `analyze_youtube_videos` tool to analyze the `video_url`.
2. Use the `query_web` tool to perform Google Searches for any concepts or entities identified in the previous step.
3. Using the results from the previous step, generate a summary describing the context of the video. For example, what is taking place? Who is involved?
4. For any insight or context gathered in previous steps, call the `call_yt_trends_generator_agent` tool to update the `yt_trends` session state.
"""

# yt_trends_generator_agent = Agent(
#     model=MODEL,
#     name="yt_trends_generator_agent",
#     instruction=yt_trends_generation_prompt,
#     disallow_transfer_to_parent=True,
#     disallow_transfer_to_peers=True,
#     generate_content_config=json_response_config,
#     output_schema=YT_Trends,
#     output_key="yt_trends",
# )

yt_trends_researcher = Agent(
    name="yt_trends_researcher",
    model=MODEL,
    instruction=_SEQ_YT_TREND_PROMPT,
    description="Researches trending YouTube videos selected by the user.",
    tools=[
        query_web,
        LongRunningFunctionTool(analyze_youtube_videos),
        call_yt_trends_generator_agent,
        # AgentTool(agent=yt_trends_generator_agent),
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    after_agent_callback=campaign_callback_function,
)
