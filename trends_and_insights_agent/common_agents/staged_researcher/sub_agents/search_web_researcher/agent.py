import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import google_search
from google.adk.planners import BuiltInPlanner
from google.adk.agents import Agent, SequentialAgent

from trends_and_insights_agent.shared_libraries import callbacks
from trends_and_insights_agent.shared_libraries.config import config


gs_web_planner = Agent(
    model=config.lite_planner_model,
    name="gs_web_planner",
    description="Generates initial queries to understand why the 'target_search_trends' are trending.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand the cultural significance of trends from Google Search.

    Review the search trend(s) provided in the **Input Data**, then proceed to the **Instructions**.

    ---
    **Input Data**

    <SEARCH_TRENDS>
    {target_search_trends}
    </SEARCH_TRENDS>
    
    ---
    **Instructions**
    1. Read the 'target_search_trends' state key to get the Search trend.
    2. Generate 4-5 queries that will provide more context for this trend, and answer questions like:
        - Why are these search terms trending? Who is involved?
        - Are there any related themes that would resonate with our target audience?
        - Describe any key entities involved (i.e., people, places, organizations, named events, etc.), and the relationships between these key entities, especially in the context of the trending topic, or if possible the target product
        - Explain the cultural significance of the trend.
    
    **CRITICAL RULE: Your output should just include a numbered list of queries. Nothing else.**
    """,
    output_key="initial_gs_queries",
)


gs_web_searcher = Agent(
    model=config.worker_model,
    name="gs_web_searcher",
    description="Performs the crucial first pass of web research about the trending Search terms.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a diligent and exhaustive researcher. 
    Your task is to conduct initial web research for the trending Search terms.
    Use the 'google_search' tool to execute all queries listed in 'initial_gs_queries'. 
    Synthesize the results into a detailed summary.
    """,
    tools=[google_search],
    output_key="gs_web_search_insights",
    after_agent_callback=callbacks.collect_research_sources_callback,
)


gs_sequential_planner = SequentialAgent(
    name="gs_sequential_planner",
    description="Executes sequential research tasks for trends in Google Search.",
    sub_agents=[gs_web_planner, gs_web_searcher],
)
