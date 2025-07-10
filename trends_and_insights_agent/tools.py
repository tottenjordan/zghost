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


# ========================
# artifacts
# ========================

# # TODO: need to load artifact for data extraction
# async def load_sample_guide(tool_context: ToolContext) -> Optional[types.Content]:
#     """
#     Loads a sample campaign guide from a public Cloud Storage bucket.
#     This function is executed upon user request, typically to quickly demo with sample data.

#     Checks if the file from GCS is already loaded as an artifact. If so, returns its details.
#     Otherwise, downloads the file, saves it as an artifact in the ADK session,
#     and returns its details.

#     Args:
#         tool_context: The execution context for the tool.
#     Returns:
#         A string confirming the file status (already loaded or newly loaded) and its details,
#         or an error message.
#     """

#     gcs_bucket = "jts-public-bucket-host"
#     gcs_file_path = f"sample-campaign-guides/[zghost]_v9_marketing_guide_Pixel_9.pdf"
#     gsutil_uri = f"gs://{gcs_bucket}/{gcs_file_path}"
#     public_url = f"https://storage.googleapis.com/{gcs_bucket}/{gcs_file_path}"

#     # a key for the artifact to be stored as:
#     file_name = gcs_file_path.split("/")[-1]
#     # artifact_key = f"gcsfile_{gcs_bucket}_{gcs_file_path.replace('/', '_')}"
#     artifact_key = "campaign_guide.pdf"

#     try:
#         # does this file already exists as an artifact?
#         existing_artifact = await tool_context.load_artifact(filename=artifact_key)

#         # it already exists:
#         if existing_artifact and isinstance(existing_artifact, types.Part):
#             file_type = existing_artifact.inline_data.mime_type
#             file_size = len(existing_artifact.inline_data.data)

#             message = (
#                 f"\nThe file {file_name} (from gs://{gcs_bucket}/{gcs_file_path}) is already loaded as an artifact!"
#                 f"Type: {file_type}, Size: {file_size} bytes, artifact_key = {artifact_key}.\n\n"
#                 f"Now let's extract the details..."
#             )
#             return message

#         # retrieve file as bytes
#         gcs = storage.Client()
#         bucket = gcs.bucket(gcs_bucket)
#         blob = bucket.blob(gcs_file_path)
#         if not blob.exists():
#             return f"Error: File not found in GCS at gs://{gcs_bucket}/{gcs_file_path}"

#         file_bytes = blob.download_as_bytes()
#         file_type = blob.content_type
#         file_ext = file_name.split(".")[-1]

#         # confirm file_type is pdf or png, else error
#         if file_type is None or file_type != "application/pdf":
#             if file_ext == "pdf":
#                 file_type = "application/pdf"
#             else:
#                 # file_type = 'application/octet-stream'
#                 return f"Error: Expected File type not found in GCS at gs://{gcs_bucket}/{gcs_file_path}. Found type {file_type}."

#         # add info to tool_context as artifact
#         file_part = types.Part.from_bytes(data=file_bytes, mime_type=file_type)
#         version = await tool_context.save_artifact(
#             filename=artifact_key, artifact=file_part
#         )
#         tool_context.state["artifact_keys"]["load_sample_guide"] = artifact_key

#         # Formulate a confirmation message
#         confirmation_message = (
#             f"\nThe file {file_name} of type {blob.content_type} and size {len(file_bytes)} bytes was loaded as an artifact!\n\n"
#             f"The `artifact_key` = {artifact_key} and `version` = {version}.\n\n"
#             f"Now let's extract the details..."
#         )
#         response = types.Content(
#             parts=[types.Part(text=confirmation_message)], role="model"
#         )

#         return response

#     except Exception as e:

#         return f"Error downloading the file: {str(e)}"


# # get uploaded PDFs
# async def get_user_file(tool_context: ToolContext) -> Optional[types.Content]:
#     """
#     Processes a newly uploaded user file, making it available for other tools.

#     This tool MUST be called as the first step immediately after a user uploads a file.
#     It accesses the file data from the user's message, and saves it as a session artifact with the key
#     'user_uploaded_file'. All other document processing tools depend on this artifact being created first.

#     Args:
#         tool_context: The execution context for the tool, which contains the user's
#                       uploaded file content.
#     Returns:
#         A string confirming the successful creation of the file artifact and its
#         details, or a clear error message if the file cannot be processed.
#     """

#     try:
#         # parts = tool_context.user_content.parts
#         parts = [
#             p for p in tool_context.user_content.parts if p.inline_data is not None
#         ]
#         if parts:
#             part = parts[-1]  # take the most recent file
#             artifact_key = "campaign_guide.pdf"
#             file_bytes = part.inline_data.data
#             file_type = part.inline_data.mime_type

#             # confirm file_type is pdf, else error
#             if file_type != "application/pdf":
#                 return f"Error: Expected File type not found. Found type {file_type}."

#             if file_type == "application/pdf":
#                 file_part = types.Part.from_bytes(data=file_bytes, mime_type=file_type)

#             # add info to tool_context as artifact
#             version = await tool_context.save_artifact(
#                 filename=artifact_key, artifact=file_part
#             )
#             tool_context.state["artifact_keys"]["get_user_file"] = artifact_key

#             # Formulate a confirmation message
#             confirmation_message = (
#                 f"\nThank you! I've successfully processed your uploaded PDF file.\n\n"
#                 f"I'm assuming this is a campaign guide. It is stored as an artifact with key "
#                 f"'{artifact_key}' (version: {version}, size: {len(file_bytes)} bytes).\n\n"
#                 f"Now let's extract the details..."
#             )
#             response = types.Content(
#                 parts=[types.Part(text=confirmation_message)], role="model"
#             )

#             return response

#         else:
#             return f"Did not find file data in the user context."
#     except Exception as e:
#         return f"Error looking for user file: {str(e)}"
