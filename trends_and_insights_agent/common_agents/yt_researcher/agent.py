from google.genai import types
from google.adk.agents import Agent

# from google.adk.agents.llm_agent import LlmAgent
# from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import LongRunningFunctionTool

# from ...shared_libraries.schema_types import json_response_config
from ...shared_libraries import callbacks
from ...utils import MODEL
from ...tools import (
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

**Available Tools:** You have access to the following tools:
*   `query_web` : Use this tool to perform web searches with Google Search.
*   `analyze_youtube_videos` : Use this tool to process and 'understand' YouTube videos.
*   `call_yt_trends_generator_agent` : Use this tool to update the `yt_trends` session state from your analysis of trending videos. Do not use this tool until **after** you have completed your web research for the trending YouTube videos.

**Instructions:** Follow these steps to complete the task at hand:
1. For each entry in the `target_yt_trends` session state, use the `analyze_youtube_videos` tool to analyze the `video_url`.
2. Use your analysis from the previous step to generate web queries that will help you better understand the trending video's content, as well as the context of why it's trending. Use the `query_web` tool to execute these queries and gather insights.
3. Given the results from the previous step, generate multiple insights that explain the video and why its trending.
4. For each insight gathered in the previous steps, call the `call_yt_trends_generator_agent` tool to store this insight in the `yt_trends` session state.

"""


yt_researcher_agent = Agent(
    name="yt_researcher_agent",
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
    after_agent_callback=callbacks.campaign_callback_function,
)
