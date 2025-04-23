# imports
import os

import googleapiclient.discovery
from google.cloud import secretmanager as sm

# clients
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

    request = youtube_client.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    )
    trend_response = request.execute()
    return trend_response
