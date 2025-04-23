# First, you need to install the library:

try:
    # The library is called 'googlesearch', but installed via 'googlesearch-python'
    from googlesearch import search

except ImportError:
    print("Could not import the 'googlesearch' library.")
    print("Please install it first using: pip install googlesearch-python")
    search = None  # Set search to None so the script doesn't crash immediately

# imports
import os
import pandas as pd
from typing import Optional 

from google import genai
from google.genai import types

import googleapiclient.discovery
from google.cloud import secretmanager as sm
from google.adk.models.llm_request import LlmRequest

# clients
client = genai.Client()

sm_client = sm.SecretManagerServiceClient()
SECRET_ID = (
    f'projects/{os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER")}/secrets/yt-data-api'
)
SECRET_VERSION = "{}/versions/1".format(SECRET_ID)
response = sm_client.access_secret_version(request={"name": SECRET_VERSION})
YOUTUBE_DATA_API_KEY = response.payload.data.decode("UTF-8")

youtube_client = googleapiclient.discovery.build(
    serviceName="youtube", version="v3", developerKey=YOUTUBE_DATA_API_KEY
)

# ========================
# yt trend tools
# ========================

def analyze_yt_videos(
    prompt: str,
    youtube_url: str,
    model: str = "gemini-2.0-flash-001",
) -> str:
    
    if "youtube.com" not in youtube_url:
        return "Not a valid youtube URL"
    else:
        video1 = types.Part.from_uri(
            file_uri=youtube_url,
            mime_type="video/*",
        )
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt), video1],
            )
        ]
        result = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_modalities=[types.Modality.TEXT],
                system_instruction="TODO",
            ),
        )
        return result.text



def get_youtube_trends(
    # part: str = "snippet,contentDetails,statistics",
    # chart: str = "mostPopular",
    region_code: str = "US",
    max_results: int = 7,
    # youtube_client: googleapiclient.discovery.Resource = youtube_client,
) -> dict:
    """
    Returns a dictionary of videos that match the API request parameters e.g., trending videos

    Args:
        region_code (str): selects a video chart available in the specified region.
            values are ISO 3166-1 alpha-2 country codes
        max_results (int): The number of video results to return.
        youtube_client (googleapiclient.discovery.Resource): The YouTube Data API client.

    Returns:
        dict: The response from the YouTube Data API.
    """

    YT_TREND_ANALYSIS_PROMPT = """
    Generate a sumamry describing what is taking place or being discussed in the video.
    Describe the key entities involved. This could be a person, place, organization or named event. This includes their backgrounds, roles, and any other relevant information.
    Describe the relationships between the key entities described in the previous step
    """

        # part (str): The parts of the video resource to include in the response.
        # chart (str): The chart to retrieve. Only 'mostPopular' is supported; returns the most popular
            # videos for the specified content region and video category.

    # https://developers.google.com/youtube/v3/docs/videos
    request = youtube_client.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    )
    trend_response = request.execute()

    trend_dict = {}
    for index, video in enumerate(trend_response["items"]):
        # the `tags` field is ommitted if video doesnt have tags
        if "tags" in video["snippet"].keys():
            TAGS_VALUE = video["snippet"]["tags"]
        else:
            TAGS_VALUE = []

        VIDEO_URL = f"https://www.youtube.com/watch?v={video['id']}"
        LLM_SUMMARY = analyze_yt_videos(
            prompt=YT_TREND_ANALYSIS_PROMPT,
            youtube_url=VIDEO_URL
        )
        trend_dict.update(
            {
                index: {
                    "videoTitle": video["snippet"]["title"],
                    "channelTitle": video["snippet"]["channelTitle"],
                    "videoDescription": video["snippet"]["description"],
                    "videoURL": VIDEO_URL,
                    "videoThumbnail": video["snippet"]["thumbnails"]["high"]["url"],
                    "videoSummary": LLM_SUMMARY,
                    # 'duration': video['contentDetails']['duration'],
                    "viewCount": video["statistics"]["viewCount"],
                    "likeCount": video["statistics"]["likeCount"],
                    "favoriteCount": video["statistics"]["favoriteCount"],
                    "commentCount": video["statistics"]["commentCount"],
                    "videoId": video["id"],
                    "channelId": video["snippet"]["channelId"],
                    "publishedAt": video["snippet"]["publishedAt"],
                    "videoTags": TAGS_VALUE,
                }
            }
        )

    return trend_dict


def search_yt(
    query: str,
    video_duration: str = "short",
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
            Must be one of: 'any', 'long', 'medium', 'short', where short=(-inf, 4), medium=[4, 20], long=(20, inf)
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
    print(f"Searching videos published after: {published_after_timestamp}")

    # Using Search:list - https://developers.google.com/youtube/v3/docs/search/list
    yt_data_api_request = youtube_client.search().list(
        type="video",
        part="id,snippet",
        relevanceLanguage="en",
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