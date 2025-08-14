"""Standalone Trends and Insights Agent for A2A Server.

This is a standalone version that doesn't conflict with the main agent hierarchy.
"""

import logging
from typing import Any, Dict

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Standalone version for a2a
standalone_trends_insights = Agent(
    model="gemini-2.5-flash-latest",
    name="trends_insights",
    description="Handles trend selection, campaign guide data extraction, and initial insights generation.",
    instruction="""You are the Trends and Insights agent responsible for trend analysis and data extraction.
    
    Your responsibilities:
    1. Display available Google Search and YouTube trends for user selection
    2. Extract and process campaign guide data from uploaded PDFs
    3. Generate initial insights based on trends and campaign data
    4. Prepare data for downstream research agents
    
    Process the input and return:
    - target_search_trends: Selected Google Search trends
    - target_yt_trends: Selected YouTube trends
    - yt_video_analysis: YouTube video summary and analysis
    - campaign_guide_data: Extracted campaign guide information
    - target_product: Identified product from campaign guide
    - target_audience: Identified target audience
    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
)