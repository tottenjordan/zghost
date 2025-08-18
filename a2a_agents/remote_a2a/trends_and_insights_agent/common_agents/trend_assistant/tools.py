import os
import logging

logging.basicConfig(level=logging.INFO)

import googleapiclient.discovery
from google.cloud import bigquery
from google.adk.tools import ToolContext

from ...shared_libraries.config import config
from ...shared_libraries.secrets import access_secret_version


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

BQ_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
bq_client = bigquery.Client(project=BQ_PROJECT)


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
    Use this tool after the user has selected trending YouTube content to target for the campaign.

    Args:
        selected_trends: dict -> The selected trends from the markdown table.
            video_title: str -> The title of the user-selected video from YouTube Trends (`videoTitle`).
            video_duration: str -> The user-selected video's duration (`duration`).
            video_url: str -> The user-selected video's URL (`videoURL`).
        tool_context: The tool context.

    Returns:
        A status message.
    """
    existing_target_yt_trends = tool_context.state.get("target_yt_trends")
    if existing_target_yt_trends is not {"target_yt_trends": []}:
        existing_target_yt_trends["target_yt_trends"].append(selected_trends)
    tool_context.state["target_yt_trends"] = existing_target_yt_trends
    return {"status": "ok"}


def get_youtube_trends(
    tool_context: ToolContext,
    region_code: str = "US",
    max_results: int = config.max_results_yt_trends,
) -> dict:
    """
    Makes request to YouTube Data API for most popular videos in a given region.
    Returns a dictionary of videos that match the API request parameters e.g., trending videos

    Args:
        tool_context: The ADK tool context.
        region_code (str): selects a video chart available in the specified region. Values are ISO 3166-1 alpha-2 country codes.
            For example, the region_code for the United Kingdom would be 'GB', whereas 'US' would represent The United States.
        max_results (int): The number of video results to return.

    Returns:
        dict: The response from the YouTube Data API.
    """

    request = youtube_client.videos().list(
        part="snippet,contentDetails",  # statistics
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    )
    trend_response = request.execute()
    # return trend_response

    # TODO: only return select fields
    trend_dict = {}
    trends_list = []  # For frontend display
    i = 1
    for video in trend_response["items"]:
        row_name = f"row_{i}"
        video_data = {
            "videoId": video["id"],
            "videoTitle": video["snippet"]["title"],
            # 'videoDescription': video['snippet']['description'],
            "duration": video["contentDetails"]["duration"],
            "videoURL": f"https://www.youtube.com/watch?v={video['id']}",
        }
        trend_dict.update({row_name: video_data})
        
        # Format for frontend
        trends_list.append({
            "id": video["id"],
            "title": video["snippet"]["title"],
            "channel": video["snippet"].get("channelTitle", ""),
            "description": video["snippet"].get("description", "")[:200] + "..." if len(video["snippet"].get("description", "")) > 200 else video["snippet"].get("description", ""),
            "duration": video["contentDetails"]["duration"],
            "url": f"https://www.youtube.com/watch?v={video['id']}",
        })
        i += 1
    
    # Save to session state for frontend
    tool_context.state["youtube_trends"] = trends_list
    logging.info(f"Saved {len(trends_list)} YouTube trends to state")
    
    return trend_dict


async def save_search_trends_to_session_state(
    new_trends: dict, tool_context: ToolContext
) -> dict:
    """
    Tool to save `new_trends` to the 'target_search_trends' state key.
    Use this tool after the user has selected a Trending Search topic to target for the campaign.

    Args:
        new_trends: The selected trends from the markdown table. Use the `tool_context` to extract the following schema:
            trend_title: str -> The trend's `term` from the markdown table. Should be the exact same words as seen in the markdown table.
            trend_rank: int -> The trend's `rank` in the markdown table. Should be the exact same number as seen in the markdown table.
            trend_refresh_date: str -> The trend's `refresh_date` from the markdown table. Should be the same date string as seen in the markdown table, and formatted as 'MM/DD/YYYY'
        tool_context: The tool context.

    Returns:
        A status message.
    """
    existing_target_search_trends = tool_context.state.get("target_search_trends")
    if existing_target_search_trends is not {"target_search_trends": []}:
        existing_target_search_trends["target_search_trends"].append(new_trends)
    tool_context.state["target_search_trends"] = existing_target_search_trends
    return {"status": "ok"}


# ==============================
# Google Search Trends (context)
# =============================
def get_gtrends_max_date() -> str:
    query = f"""
        SELECT 
         MAX(refresh_date) as max_date
        FROM `bigquery-public-data.google_trends.top_terms`
    """
    max_date = bq_client.query(query).to_dataframe()
    return max_date.iloc[0, 0].strftime("%m/%d/%Y")


max_date = get_gtrends_max_date()


def get_daily_gtrends(tool_context: ToolContext, today_date: str = max_date) -> dict:
    """
    Retrieves the top 25 Google Search Trends (term, rank, refresh_date).

    Args:
        tool_context: The ADK tool context.
        today_date: Today's date in the format 'MM/DD/YYYY'. Use the default value provided.

    Returns:
        dict: key is the latest date for the trends, the value is a markdown table containing the Google Search Trends.
             The table includes columns for 'term', 'rank', and 'refresh_date'.
             Returns 25 terms ordered by their rank (ascending order) for the current week.
    """
    # get latest refresh date
    max_date = get_gtrends_max_date()
    # max_date = "07/15/2025"
    logging.info(f"\n\nmax_date in trends_assistant: {max_date}\n\n")

    query = f"""
        SELECT
          term,
          refresh_date,
          ARRAY_AGG(STRUCT(rank,week) ORDER BY week DESC LIMIT 1) x
        FROM `bigquery-public-data.google_trends.top_terms`
        WHERE refresh_date = PARSE_DATE('%m/%d/%Y',  '{max_date}')
        GROUP BY term, refresh_date
        ORDER BY (SELECT rank FROM UNNEST(x))
        """
    try:
        df_t = bq_client.query(query).to_dataframe()
        df_t.index += 1
        df_t["rank"] = df_t.index
        df_t = df_t.drop("x", axis=1)
        new_order = ["term", "rank", "refresh_date"]
        df_t = df_t[new_order]
        markdown_string = df_t.to_markdown(index=True)
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

    # Save trends for frontend
    google_trends_list = []
    for _, row in df_t.iterrows():
        google_trends_list.append({
            "name": row["term"],
            "rank": int(row["rank"]),
            "refresh_date": row["refresh_date"].strftime("%m/%d/%Y") if hasattr(row["refresh_date"], 'strftime') else str(row["refresh_date"]),
        })
    tool_context.state["google_trends"] = google_trends_list
    logging.info(f"Saved {len(google_trends_list)} Google trends to state")
    
    return {
        "status": "ok",
        "markdown_table": markdown_string,
    }
