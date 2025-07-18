import os
import logging

logging.basicConfig(level=logging.INFO)

import pandas as pd
from typing import Optional
import googleapiclient.discovery
from google.genai import types, Client

from .shared_libraries.config import config
from .shared_libraries.secrets import access_secret_version


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

# google genai client
client = Client()


# ========================
# YouTube tools
# ========================
def query_youtube_api(
    query: str,
    video_duration: str,
    video_order: str = "relevance",
    num_video_results: int = 5,
    max_num_days_ago: int = 30,
    video_caption: str = "closedCaption",
    channel_type: Optional[str] = "any",
    channel_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> dict:
    """
    Gets a response from the YouTube Data API for a given search query.

    Args:
        query (str): The search query.
        video_duration (str): The duration (minutes) of the videos to search for.
            Must be one of: 'any', 'long', 'medium', 'short', where short=(-inf, 4),
            medium=[4, 20], long=(20, inf)
        video_order (str): The order in which the videos should be returned.
            Must be one of 'date', 'rating', 'relevance', 'title', 'viewCount'
        num_video_results (int): The number of video results to return.
        max_num_days_ago (int): The maximum number of days ago the videos should have been published.
        youtube_client (googleapiclient.discovery.Resource): The YouTube Data API client.
        video_caption (str): whether API should filter video search results based on whether they have captions.
            Must be one of "any", "closedCaption", "none"
            "any" = Do not filter results based on caption availability.
            "closedCaption" = Only include videos with closed captions.
            "none" = Only include videos that do not have captions.
        channel_type (Optional[str]): The type of channel to search within.
            Must be one of "show", "any", or "channelTypeUnspecified". Specifying "show" retrieves only TV shows
        channel_id (Optional[str]): The ID of the channel to search within.
        eventType (str): restricts a search to broadcast events. Must be one of "upcoming", "live", "completed", None
            None = does not restrict to broadcast events
            "completed" = Only include completed broadcasts.
            "live" = Only include active broadcasts.
            "upcoming" = Only include upcoming broadcasts.

    Returns:
        dict: The response from the YouTube Data API.
    """

    published_after_timestamp = (
        (pd.Timestamp.now() - pd.DateOffset(days=max_num_days_ago))
        .tz_localize("UTC")
        .isoformat()
    )

    # Using Search:list - https://developers.google.com/youtube/v3/docs/search/list
    yt_data_api_request = youtube_client.search().list(
        type="video",
        part="id,snippet",
        relevanceLanguage="en",
        regionCode="US",
        q=query,
        videoDuration=video_duration,
        order=video_order,
        maxResults=num_video_results,
        videoCaption=video_caption,
        channelType=channel_type,
        channelId=channel_id,
        eventType=event_type,
        publishedAfter=published_after_timestamp,
    )
    yt_data_api_response = yt_data_api_request.execute()
    return yt_data_api_response


# region_code: str = "US",
# region_code (str): selects a video chart available in the specified region.
#     Values are ISO 3166-1 alpha-2 country codes. For example, the region_code for the United Kingdom would be 'GB',
#     whereas 'US' would represent The United States.


def analyze_youtube_videos(
    prompt: str,
    youtube_url: str,
) -> Optional[str]:
    """
    Analyzes youtube videos given a prompt and the video's URL

    Args:
        prompt (str): The prompt to use for the analysis.
        youtube_url (str): The url to check for youtube.com
    Returns:
        Results from the youtube video analysis prompt.
    """

    if "youtube.com" not in youtube_url:
        return "Not a valid youtube URL"
    else:
        video = types.Part.from_uri(
            file_uri=youtube_url,
            mime_type="video/*",
        )
        contents = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt), video],
        )
        result = client.models.generate_content(
            model=config.video_analysis_model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )
        if result and result.text is not None:

            return result.text
