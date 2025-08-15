"""Trends and Insights A2A Server Agent.

This agent handles trend selection, data extraction from campaign guides,
and initial insights generation.
"""

import os
import logging
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import ToolContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config
from .config import config


def memorize(key: str, value: str, tool_context: ToolContext):
    """
    Memorize pieces of information, one key-value pair at a time.
    
    Args:
        key: the label indexing the memory to store the value.
        value: the information to be stored.
        tool_context: The ADK tool context.
    
    Returns:
        A status message.
    """
    mem_dict = tool_context.state
    mem_dict[key] = value
    return {"status": f'Stored "{key}": "{value}"'}


async def save_yt_trends_to_session_state(
    selected_trends: dict, tool_context: ToolContext
) -> dict:
    """
    Tool to save `selected_trends` to the 'target_yt_trends' state key.
    
    Args:
        selected_trends: dict -> The selected trends from the markdown table.
        tool_context: The tool context.
    
    Returns:
        A status message.
    """
    existing_target_yt_trends = tool_context.state.get("target_yt_trends", {"target_yt_trends": []})
    if existing_target_yt_trends != {"target_yt_trends": []}:
        existing_target_yt_trends["target_yt_trends"].append(selected_trends)
    tool_context.state["target_yt_trends"] = existing_target_yt_trends
    return {"status": "ok"}


async def save_search_trends_to_session_state(
    new_trends: dict, tool_context: ToolContext
) -> dict:
    """
    Tool to save `new_trends` to the 'target_search_trends' state key.
    
    Args:
        new_trends: The selected trends from the markdown table.
        tool_context: The tool context.
    
    Returns:
        A status message.
    """
    existing_target_search_trends = tool_context.state.get("target_search_trends", {"target_search_trends": []})
    if existing_target_search_trends != {"target_search_trends": []}:
        existing_target_search_trends["target_search_trends"].append(new_trends)
    tool_context.state["target_search_trends"] = existing_target_search_trends
    return {"status": "ok"}


def get_youtube_trends(
    tool_context: ToolContext,
    region_code: str = "US",
    max_results: int = 10,
) -> dict:
    """
    Mock function to get YouTube trends for a2a demo.
    
    Args:
        tool_context: The ADK tool context.
        region_code: Region code for trends.
        max_results: Number of results to return.
    
    Returns:
        dict: Mock YouTube trends data.
    """
    # Mock data for demo purposes
    trends_list = [
        {
            "id": "demo1",
            "title": "Trending Video 1",
            "channel": "Popular Channel",
            "description": "This is a trending video about...",
            "duration": "PT10M30S",
            "url": "https://www.youtube.com/watch?v=demo1",
        },
        {
            "id": "demo2",
            "title": "Trending Video 2",
            "channel": "Another Channel",
            "description": "Another trending video about...",
            "duration": "PT5M15S",
            "url": "https://www.youtube.com/watch?v=demo2",
        },
    ]
    
    # Save to session state
    tool_context.state["youtube_trends"] = trends_list[:max_results]
    
    # Return in expected format
    trend_dict = {}
    for i, video in enumerate(trends_list[:max_results], 1):
        trend_dict[f"row_{i}"] = {
            "videoId": video["id"],
            "videoTitle": video["title"],
            "duration": video["duration"],
            "videoURL": video["url"],
        }
    
    return trend_dict


def get_daily_gtrends(tool_context: ToolContext, today_date: str = "01/15/2025") -> dict:
    """
    Mock function to get Google Search trends for a2a demo.
    
    Args:
        tool_context: The ADK tool context.
        today_date: Date for trends.
    
    Returns:
        dict: Mock Google Search trends data.
    """
    # Mock data for demo purposes
    trends_data = """
| term | rank | refresh_date |
|------|------|--------------|
| trending topic 1 | 1 | 01/15/2025 |
| trending topic 2 | 2 | 01/15/2025 |
| trending topic 3 | 3 | 01/15/2025 |
| trending topic 4 | 4 | 01/15/2025 |
| trending topic 5 | 5 | 01/15/2025 |
"""
    
    # Save to session state
    trends_list = [
        {"term": f"trending topic {i}", "rank": i, "refresh_date": today_date}
        for i in range(1, 6)
    ]
    tool_context.state["search_trends"] = trends_list
    
    return {
        "Latest Google Search Trends": trends_data,
        "refresh_date": today_date,
    }


# Agent instruction
AUTO_TREND_AGENT_INSTR = """You are a marketing assistant that helps users select trending topics for their campaigns.

Your main responsibilities:
1. Display available trending topics from Google Search and YouTube
2. Help users understand and select relevant trends
3. Extract and save campaign metadata from uploaded PDFs
4. Provide initial insights based on selected trends

Use the available tools to:
- `get_daily_gtrends`: Fetch current Google Search trends
- `get_youtube_trends`: Fetch current YouTube trending videos
- `save_search_trends_to_session_state`: Save selected Google Search trends
- `save_yt_trends_to_session_state`: Save selected YouTube trends
- `memorize`: Store important campaign information

Always be helpful and guide users through the trend selection process."""


# Create root_agent for a2a protocol
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
)