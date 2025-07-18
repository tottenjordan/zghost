import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent

from .tools import (
    get_daily_gtrends,
    get_youtube_trends,
    save_yt_trends_to_session_state,
    save_search_trends_to_session_state,
    memorize,
)
from .prompts import AUTO_TREND_AGENT_INSTR_v2
from ...shared_libraries.config import config

# TODO: add this here
# campaign_guide_data_extract_agent = Agent(
#     model=config.worker_model,
#     name="campaign_guide_data_extract_agent",
#     description="Captures campaign details if user uploads PDF.",
#     instruction=GUIDE_DATA_EXTRACT_INSTR,
#     disallow_transfer_to_parent=True,
#     disallow_transfer_to_peers=True,
#     generate_content_config=schema_types.json_response_config,
#     output_schema=schema_types.MarketingCampaignGuide,
#     output_key="campaign_guide",
# )

trends_and_insights_agent = Agent(
    model=config.worker_model,
    name="trends_and_insights_agent",
    description="Captures campaign metadata and displays trending topics from Google Search and trending videos from YouTube.",
    instruction=AUTO_TREND_AGENT_INSTR_v2,
    tools=[
        get_daily_gtrends,
        get_youtube_trends,
        save_yt_trends_to_session_state,
        save_search_trends_to_session_state,
        memorize,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
