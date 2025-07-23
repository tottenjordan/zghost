import os
import re
import datetime
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.planners import BuiltInPlanner
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search

from trends_and_insights_agent.shared_libraries import callbacks
from trends_and_insights_agent.shared_libraries.config import config
from trends_and_insights_agent.tools import analyze_youtube_videos


yt_analysis_generator_agent = Agent(
    model=config.worker_model,
    name="yt_analysis_generator_agent",
    description="Process YouTube videos, extract key details, and provide an overall summary.",
    instruction="""
    Your goal is to **understand the content** of the trending YouTube video in the 'target_yt_trends' state key.
    
    1. Review the 'target_yt_trends' state key and use the `analyze_youtube_videos` tool to analyze the 'video_url'.
    2. Provide a concise summary covering:
        - **Main Thesis/Claim:** What is the video about? What is being discussed?
        - **Key Entities:** Describe any key entities (e.g., people, places, things) involved and how they are related. 
        - **Trend Context:** Why might this video be trending?
        - **Summary:** Provide a concise summary of the video content.
    """,
    tools=[analyze_youtube_videos],
    output_key="yt_video_analysis",
)


yt_web_planner = Agent(
    model=config.lite_planner_model,
    name="yt_web_planner",
    include_contents="none",
    description="Generates initial queries to understand why the 'target_yt_trends' are trending.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand the cultural significance of the selected trending YouTube video(s) in the 'target_yt_trends' state key.
    
    Review the trending YouTube video and analysis provided in the **Input Data**, then proceed to the **Instructions**.

    ---
    ### Input Data

    <target_yt_trends>
    {target_yt_trends}
    </target_yt_trends>

    <yt_video_analysis>
    {yt_video_analysis}
    </yt_video_analysis>

    ---
    ### Instructions
    1. Read the 'target_yt_trends' and 'yt_video_analysis' state keys to understand the trending YouTube video.
    2. Generate 2-3 web queries to better understanding the context of the video.
    
    Your output should just include a numbered list of queries. Nothing else.
    """,
    output_key="initial_yt_queries",
)


yt_web_searcher = Agent(
    model=config.worker_model,
    name="yt_web_searcher",
    description="Performs web research to better understand the context of the trending YouTube video.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a diligent and exhaustive researcher. 
    Your task is to conduct initial web research for concepts described in the 'yt_video_analysis' state key.
    You will be provided with a list of web queries in the 'initial_yt_queries' state key.
    Execute all of these queries using the 'google_search' tool and synthesize the results into a detailed summary
    """,
    tools=[google_search],
    output_key="yt_web_search_insights",
    after_agent_callback=callbacks.collect_research_sources_callback,
)


yt_sequential_planner = SequentialAgent(
    name="yt_sequential_planner",
    description="Executes sequential research tasks for trending YouTube videos.",
    sub_agents=[yt_analysis_generator_agent, yt_web_planner, yt_web_searcher],
)
