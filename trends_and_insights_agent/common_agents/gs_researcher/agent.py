import os
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import ToolContext, google_search

from ...shared_libraries import callbacks, schema_types
from ...prompts import search_trends_generation_prompt
from ...utils import MODEL
from ...tools import query_web


search_trends_generator_agent = Agent(
    model=MODEL,
    name="search_trends_generator_agent",
    description="Gathers research insights about trending Search terms.",
    instruction=search_trends_generation_prompt,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=schema_types.json_response_config,
    output_schema=schema_types.Search_Trends,
    output_key="search_trends",
)


async def call_search_trends_generator_agent(
    question: str, tool_context: ToolContext
) -> dict:
    """
    Tool to call `search_trends_generator_agent`.
    This tool updates the `search_trends` in session state with insights gathered from web research.

    Args:
        Question: The question to ask the agent, use the tool_context to extract the following schema:
            trend_title: str -> Come up with a unique title to represent the trend. Structure this title so it begins with the exact words from the 'trending topic` followed by a colon and a witty catch-phrase.
            trend_text: str -> Generate a summary describing what happened with the trending topic and what is being discussed.
            trend_urls: list[str] -> List any url(s) that provided reliable context.
            key_entities: list[str] -> Extract any key entities discussed in the gathered context.
            key_relationships: list[str] -> Describe the relationships between the key entities you have identified.
            key_audiences: list[str] -> How will this trend resonate with our target audience(s), `campaign_guide.target_audience`?
            key_product_insights: list[str] -> Suggest how this trend could possibly intersect with the target product: `campaign_guide.target_product`
        tool_context: The ADK tool context.
    """
    agent_tool = AgentTool(search_trends_generator_agent)
    existing_search_trends = tool_context.state.get("search_trends")
    search_trends = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    if existing_search_trends is not {"search_trends": []}:
        search_trends["search_trends"].extend(existing_search_trends["search_trends"])
    tool_context.state["search_trends"] = search_trends
    logging.info(f"\n\n Final `search_trends`: {search_trends} \n\n")
    return {"status": "ok"}


# Researcher 3: trending Search
_SEQ_GS_TREND_PROMPT = """**Role:** You are a Research Assistant specializing in Search trends.

**Objective:** Your goal is to conduct targeted research to better understand the cultural significance of the trending Search terms. Your research should answer questions like:
*   Why are these search terms trending? Who is involved?
*   Are there any related themes that would resonate with our target audience?
*   Describe any key entities involved (i.e., people, places, organizations, named events, etc.), and the relationships between these key entities, especially in the context of the trending topic, or if possible the target product
*   Explain the cultural significance of the trend. 

**Available Tools:** You have access to the following tools:
*   `query_web` : Use this tool to perform web searches with Google Search.
*   `call_search_trends_generator_agent` : Use this tool to generate insights from the research conducted on trending Search terms. Do not use this tool until **after** you have completed your web research for the trending YouTube videos.

**Instructions:** Follow these steps to complete your objective:
1. Use the `query_web` tool to perform several Google Searches related to the search trends in `target_search_trends` (e.g., Why are these search terms trending? Who is involved?).
2. Use insights from the results in the previous step to generate a second round of Google Searches that provide more context for the trend (e.g., key entities involved, themes that resonate with target audience, etc.). Use the `query_web` tool to execute these queries.
3. Given the results from the previous step, generate some insights that help establish a clear understanding for why this topic is trending.
4. For each insight gathered in the previous steps, call the `call_search_trends_generator_agent` tool to store them in the list of structured `search_trends` in the session state.
5. Confirm with the user before proceeding. Once the user is satisfied, transfer to the `root_agent`.

"""

gs_researcher_agent = Agent(
    name="gs_researcher_agent",
    model=MODEL,
    instruction=_SEQ_GS_TREND_PROMPT,
    description="Conducts web research to provide additional context for trending topics in Google Search",
    tools=[
        query_web,
        # google_search,
        call_search_trends_generator_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    after_agent_callback=callbacks.campaign_callback_function,
)
