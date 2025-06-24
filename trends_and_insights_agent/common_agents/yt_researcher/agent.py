import os
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import LongRunningFunctionTool

from ...shared_libraries import callbacks, schema_types
from ...prompts import yt_trends_generation_prompt
from ...utils import MODEL
from ...tools import (
    query_web,
    analyze_youtube_videos,
)


yt_trends_generator_agent = Agent(
    model=MODEL,
    name="yt_trends_generator_agent",
    description="Gathers research insights about trending YouTube videos.",
    instruction=yt_trends_generation_prompt,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=schema_types.json_response_config,
    output_schema=schema_types.YT_Trends,
    output_key="yt_trends",
)


async def call_yt_trends_generator_agent(
    question: str, tool_context: ToolContext
) -> dict:
    """
    Tool to call the `yt_trends_generator_agent` agent.
    This tool checks the session state for any trends in `target_yt_trends`,
        and for each new trend, updates `yt_trends` in the session state.

    Args:
        Question: The question to ask the agent, use the tool_context to extract the following schema:
            video_title: str -> Get the video's title from its entry in `target_yt_trends`
            trend_urls: list[str] -> Get the URL from its entry in `target_yt_trends`
            trend_text: str -> Use the `analyze_youtube_videos` tool to generate a summary of the trending video. What are the main themes?
            key_entities: list[str] -> Extract any key entities present in the trending video (e.g., people, places, things).
            key_relationships: list[str] -> Describe any relationships between the key entities.
            key_audiences: list[str] -> How will the themes in this trending video resonate with our target audience(s)?
            key_product_insights: list[str] -> Suggest how this trend could possibly intersect with the `target_product`.
        tool_context: The ADK tool context.
    """
    agent_tool = AgentTool(yt_trends_generator_agent)
    existing_yt_trends = tool_context.state.get("yt_trends")
    yt_trends = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    if existing_yt_trends is not {"yt_trends": []}:
        yt_trends["yt_trends"].extend(existing_yt_trends["yt_trends"])
    tool_context.state["yt_trends"] = yt_trends
    logging.info(f"\n\n Final `yt_trends`: {yt_trends} \n\n")
    return {"status": "ok"}


# Researcher 2: trending YouTube
_SEQ_YT_TREND_PROMPT = """**Role:** You are a Research Assistant specializing in YouTube trends.

**Objective:** Your goal is to conduct web research to gather insights related to the trending YouTube video(s). These insights should answer questions like:
*   What is the video about? what is being discussed? Who is involved?
*   Why is this video trending? 
*   Are there any themes that would resonate with our target audience(s)?

**Available Tools:** You have access to the following tools:
*   `query_web` : Use this tool to perform web searches with Google Search.
*   `analyze_youtube_videos` : Use this tool to process and 'understand' YouTube videos.
*   `call_yt_trends_generator_agent` : Use this tool to generate insights from the research conducted on trending YouTube videos. Do not use this tool until **after** you have completed your web research for the trending YouTube videos.

**Instructions:** Follow these steps to complete the task at hand:
1. For each entry in the `target_yt_trends` session state, use the `analyze_youtube_videos` tool to analyze the `video_url`.
2. Use your analysis from the previous step to create web queries that will help you better understand the trending video's content, as well as the context of why it's trending. Use the `query_web` tool to execute these queries and gather insights.
3. Given the results from the previous step, generate multiple insights that explain the video and why its trending.
4. For each insight gathered in the previous steps, call the `call_yt_trends_generator_agent` tool to store this insight in the `yt_trends` session state.
5. Confirm with the user before proceeding. Once the user is satisfied, transfer to the `root_agent`.

"""

yt_researcher_agent = Agent(
    name="yt_researcher_agent",
    model=MODEL,
    instruction=_SEQ_YT_TREND_PROMPT,
    description="Conducts web research specifically to provide additional context for trending YouTube videos.",
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
