# imports
import os
import logging

logging.basicConfig(level=logging.INFO)

import tabulate
import pandas as pd
from typing import Any
from pydantic import BaseModel, Field

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

import googleapiclient.discovery
from google.cloud import bigquery

# from google.cloud import secretmanager as sm

from ...utils import MODEL
from ...secrets import access_secret_version


# ========================
# clients
# ========================
try:
    yt_secret_id = os.environ["YT_SECRET_MNGR_NAME"]
except KeyError:
    raise Exception("YT_SECRET_MNGR_NAME environment variable not set")

# youtube client
YOUTUBE_DATA_API_KEY = access_secret_version(secret_id=yt_secret_id, version_id="1")
youtube_client = googleapiclient.discovery.build(
    serviceName="youtube", version="v3", developerKey=YOUTUBE_DATA_API_KEY
)
# bigquery client # TODO: add to .env
BQ_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
BQ_DATASET = "google_trends_copy"  # os.environ["BQ_DATASET"]
bq_client = bigquery.Client(project=BQ_PROJECT)


async def save_yt_trends_to_session_state(
    selected_trends: dict, tool_context: ToolContext
) -> dict:
    """
    Tool to save `selected_trends` to the `target_yt_trends` in the session state.
    Use this tool after the user has selected trending YouTube content to target for the campaign.

    Args:
        selected_trends: dict -> The selected trends from the markdown table.
            video_title: str -> The title of the user-selected video from YouTube Trends.
            video_duration: str -> The user-selected video's duration.
            video_url: str -> The user-selected video's URL.
        tool_context: The tool context.
    """
    existing_target_yt_trends = tool_context.state.get("target_yt_trends")
    # logging.info(f"selected_trends: {selected_trends}")
    # logging.info(f"Existing target_yt_trends: {existing_target_yt_trends}")

    if existing_target_yt_trends is not {"target_yt_trends": []}:
        existing_target_yt_trends["target_yt_trends"].append(selected_trends)
    tool_context.state["target_yt_trends"] = existing_target_yt_trends

    # logging.info(f"\n\n final state value: {existing_target_yt_trends} \n\n")
    return {"status": "ok"}


def get_youtube_trends(
    region_code: str,
    max_results: int = 5,
) -> dict:
    """
    Makes request to YouTube Data API for most popular videos in a given region.
    Returns a dictionary of videos that match the API request parameters e.g., trending videos

    Args:
        region_code (str): selects a video chart available in the specified region. Values are ISO 3166-1 alpha-2 country codes.
            For example, the region_code for the United Kingdom would be 'GB', whereas 'US' would represent The United States.
        max_results (int): The number of video results to return.

    Returns:
        dict: The response from the YouTube Data API.
    """

    request = youtube_client.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    )
    trend_response = request.execute()
    return trend_response


async def save_search_trends_to_session_state(
    new_trends: dict, tool_context: ToolContext
) -> dict:
    """
    Tool to call the `target_search_trends_generator_agent` agent and update the `target_search_trends` in the session state.
    Use this tool after the user has selected a Trending Search topic to target for the campaign.

    Args:
        Question: The question to ask the agent, use the tool_context to extract the following schema:
            trend_title: str -> The trend's `term` from the markdown table. Should be the exact same words as seen in the markdown table.
            trend_rank: int -> The trend's `rank` in the markdown table. Should be the exact same number as seen in the markdown table.
            trend_refresh_date: str -> The trend's `refresh_date` from the markdown table. Should be the same date string as seen in the markdown table, and formatted as 'MM/DD/YYYY'
        tool_context: The tool context.
    """
    existing_target_search_trends = tool_context.state.get("target_search_trends")
    # logging.info(f"new_trends: {new_trends}")
    # logging.info(f"Existing target_search_trends: {existing_target_search_trends}")

    if existing_target_search_trends is not {"target_search_trends": []}:
        existing_target_search_trends["target_search_trends"].append(new_trends)
    tool_context.state["target_search_trends"] = existing_target_search_trends

    # logging.info(f"\n\n final state value: {existing_target_search_trends} \n\n")
    return {"status": "ok"}


# ==============================
# Google Search Trends (context)
# =============================
def get_gtrends_max_date() -> str:
    query = f"""
        SELECT 
         MAX(refresh_date) as max_date
        -- FROM `{BQ_PROJECT}.{BQ_DATASET}.top_terms`
        FROM `bigquery-public-data.google_trends.top_terms`
    """
    max_date = bq_client.query(query).to_dataframe()
    return max_date.iloc[0][0].strftime("%m/%d/%Y")


def get_daily_gtrends() -> str:
    """
    Retrieves the top 25 Google Search Trends (term, rank, refresh_date) from a BigQuery table.

    Returns:
        str: a markdown table containing the Google Search Trends.
             The table includes columns for 'term', 'rank', and 'refresh_date'.
             Returns 25 terms ordered by their rank (ascending order) for the current week.
    """
    # get latest refresh date
    # max_date = get_gtrends_max_date()
    max_date = "06/18/2025"
    logging.info(f"\n\nmax_date in trends_assistant: {max_date}\n\n")

    query = f"""
        SELECT
          term,
          refresh_date,
          ARRAY_AGG(STRUCT(rank,week) ORDER BY week DESC LIMIT 1) x
        -- FROM `{BQ_PROJECT}.{BQ_DATASET}.top_terms`
        FROM `bigquery-public-data.google_trends.top_terms`
        WHERE refresh_date = PARSE_DATE('%m/%d/%Y',  '{max_date}')
        GROUP BY term, refresh_date
        ORDER BY (SELECT rank FROM UNNEST(x))
        """
    df_t = bq_client.query(query).to_dataframe()
    df_t.index += 1
    df_t["rank"] = df_t.index
    df_t = df_t.drop("x", axis=1)
    new_order = ["term", "rank", "refresh_date"]
    df_t = df_t[new_order]
    markdown_string = df_t.to_markdown(index=True)

    return f"""# Google Search Trends: \n{markdown_string}"""

    # return print(df_t.to_markdown(index=False))
    # return {"markdown_string": df_t.to_markdown(index=False)}
