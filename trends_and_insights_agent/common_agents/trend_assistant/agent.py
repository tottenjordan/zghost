import logging

logging.basicConfig(level=logging.INFO)
from typing import Dict, Any, Optional

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool

from .tools import (
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
)
from .prompts import AUTO_TREND_AGENT_INSTR
from ...shared_libraries.config import config


# TODO: add AgentTool for Search Trends, YouTube Trends


# --- 1. Define the Callback Function ---
async def process_toolbox_output(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[str]:  # Optional[Dict]:
    """
    Inspects/modifies the tool result after execution.
    """
    # get tool response information
    agent_name = tool_context.agent_name
    response = tool_response  # .get("result", "")
    logging.info(f"\n\n ## JT DEBUGGING - BEGIN ## \n\n")
    logging.info(f"--- `process_toolbox_output` ---")
    logging.info(f"\n\n agent_name: {agent_name}\n\n")
    logging.info(f"\n\n tool.name: {tool.name}\n\n")
    logging.info(f"\n\n response: {response} .\n\n")
    # if tool.name == "campaign_guide_data_extract_agent":

    # passthrough response
    return None


trends_and_insights_agent = Agent(
    model=config.worker_model,
    name="trends_and_insights_agent",
    description="Displays trending topics from Google Search and trending videos from YouTube.",
    instruction=AUTO_TREND_AGENT_INSTR,
    tools=[
        get_daily_gtrends,
        get_youtube_trends,
        save_yt_trends_to_session_state,
        save_search_trends_to_session_state,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    # after_tool_callback=process_toolbox_output,
)
