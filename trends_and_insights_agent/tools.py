import os
import logging

logging.basicConfig(level=logging.INFO)

try:
    # The library is called 'googlesearch', but installed via 'googlesearch-python'
    from googlesearch import search

except ImportError:
    logging.exception("Could not import the 'googlesearch' library.")
    logging.exception("Please install it first using: pip install googlesearch-python")
    search = None  # Set search to None so the script doesn't crash immediately

# import asyncio
# import aiohttp
# import trafilatura
import pandas as pd
from typing import Optional

from pydantic import BaseModel
from google.adk.agents import Agent
from google.genai import types, Client
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from google.cloud import secretmanager as sm
import googleapiclient.discovery
from google.cloud import storage

from .utils import MODEL
from .secrets import access_secret_version
from .shared_libraries.schema_types import (
    Insights,
    YT_Trends,
    Search_Trends,
    json_response_config,
)

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


# ========================
# search tools
# ========================
def perform_google_search(
    query: str,
    num_results: int = 10,
    lang: str = "en",
    pause_time: int = 2,
) -> list:
    # ) -> AsyncGenerator[list, None]:
    """
    Performs a Google search for a given query using the googlesearch-python library.

    Args:
        query (str): The search term.
        num_results (int): The desired number of search results to retrieve.
        lang (str): The language code for the search (e.g., 'en', 'es').
        pause_time (int): Seconds to pause between HTTP requests to avoid blocking.

    Returns:
        list: A list of URLs found for the query, or an empty list if an error occurs
              or the library wasn't imported.
    """
    if not search:
        logging.info("Googlesearch library not available. Cannot perform search.")
        return []

    search_results_urls = []
    logging.info(f"Searching Google for: '{query}' (up to {num_results} results)...")
    try:
        # The search function returns a generator. We convert it to a list.
        #   [[1](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAIt0WzakIytkvxX-NyLXvi8MeY_Lt0gOuYicrDUrmlo-oMJU5YQyD8tzXvLuLEhWcYU9l5rdXcKddjNmU0AEb2_LVzo3sGqCr7_xnWMkqIUtpuW9_rohiniNpWh0CQoxZKz1tXlOg==)]
        # 'stop=num_results' ensures we try to fetch exactly that many.
        # 'pause' helps avoid getting temporarily blocked by Google.
        results_generator = search(
            query, num_results=num_results, lang=lang, sleep_interval=pause_time
        )
        search_results_urls = list(results_generator)

        logging.info(f"Found {len(search_results_urls)} results.")

    except Exception as e:
        logging.exception(f"An error occurred during the Google search: {e}")
        logging.info(
            "This might be due to network issues or Google blocking the request."
        )
        logging.info("Try increasing the 'pause_time' or searching less frequently.")

    return search_results_urls


# async def extract_main_text_from_url(
#     url: str,
#     session: aiohttp.ClientSession,  # Pass the session for reuse
#     timeout: int = 15,
#     include_tables: bool = False,
#     favour_precision: bool = True,
# ) -> Optional[str]:  # Returns a single string or None
#     """
#     Fetches a webpage asynchronously and extracts the main textual content using trafilatura.

#     Args:
#         url (str): The URL of the webpage to scrape.
#         session (aiohttp.ClientSession): The aiohttp session to use for requests.
#         timeout (int): Max time in seconds to wait for the server response.
#         include_tables (bool): Whether to include text found within HTML tables.
#         favour_precision (bool): If True, prioritizes accuracy over recall.

#     Returns:
#         Optional[str]: The extracted main text content, or None if an error occurs.
#     """
#     headers = {
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
#         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,*/*;q=0.8",
#         "Accept-Language": "en-US,en;q=0.9",
#     }

#     extracted_text = None
#     logging.info(f"Attempting to fetch URL: {url}")

#     try:
#         async with session.get(
#             url, headers=headers, timeout=timeout, allow_redirects=True
#         ) as response:
#             # Raise an HTTPError for bad responses (4xx or 5xx)
#             # aiohttp doesn't raise by default like requests, so we check status
#             if response.status >= 400:
#                 logging.info(f"HTTP Error {response.status} for URL {url}")
#                 # Optionally raise an exception or just return None
#                 # response.raise_for_status() # This would raise ClientResponseError
#                 return None  # Return None on client/server errors

#             # Check content type (optional)
#             content_type = response.headers.get("content-type", "").lower()
#             if "text/html" not in content_type:
#                 logging.info(
#                     f"Warning: Content-Type for {url} is '{content_type}'. Extraction might be suboptimal."
#                 )

#             # Read the response content as bytes (best for trafilatura)
#             html_content = await response.read()

#             # Run trafilatura extraction (potentially blocking, see note below)
#             logging.info(f"Extracting main content from {url} using trafilatura...")
#             # Note: trafilatura itself is synchronous CPU-bound code.
#             # For *very* heavy pages or *many* concurrent tasks on a limited machine,
#             # you *might* consider running this part in a thread pool executor too,
#             # using loop.run_in_executor(None, trafilatura.extract, ...),
#             # but often the network I/O is the main bottleneck, so direct call is fine.
#             extracted_text = trafilatura.extract(
#                 html_content,
#                 include_comments=False,
#                 include_tables=include_tables,
#                 favor_precision=favour_precision,
#                 # target_language='en' # Optional
#             )

#             if not extracted_text and favour_precision:
#                 logging.info(
#                     f"Precision mode yielded no text for {url}, trying recall mode..."
#                 )
#                 extracted_text = trafilatura.extract(
#                     html_content,
#                     include_comments=False,
#                     include_tables=include_tables,
#                     favor_recall=True,  # Switch to favouring recall
#                 )

#             if extracted_text:
#                 logging.info(
#                     f"Successfully extracted content from {url} (approx. {len(extracted_text)} chars)."
#                 )
#             else:
#                 # Check if original response text had *any* text
#                 try:
#                     # Try decoding for the check, ignore errors
#                     page_text = html_content.decode(errors="ignore")
#                     if page_text and len(page_text.strip()) > 0:
#                         logging.info(
#                             f"Trafilatura could not extract main content from {url}, though the page was fetched."
#                         )
#                     else:
#                         logging.info(
#                             f"The fetched page {url} appears to have no text content."
#                         )
#                 except Exception:  # Guard against decoding errors just for the print
#                     logging.exception(
#                         f"Trafilatura could not extract main content from {url} (and checking raw text failed)."
#                     )

#                 extracted_text = None  # Ensure None is returned if extraction fails

#     except aiohttp.ClientError as e:
#         # Handles client-side exceptions like connection errors, timeouts
#         logging.exception(f"Aiohttp client error fetching URL {url}: {e}")
#         extracted_text = None
#     except asyncio.TimeoutError:
#         logging.exception(f"Timeout error fetching URL {url} after {timeout} seconds.")
#         extracted_text = None
#     except Exception as e:
#         # Catch potential unexpected errors during extraction or other issues
#         logging.exception(
#             f"An unexpected error occurred for URL {url}: {type(e).__name__} - {e}"
#         )
#         extracted_text = None

#     # No yield needed, just return the final result for this URL
#     return extracted_text


# async def query_web(
#     query: str,
#     num_results: int = 10,
#     lang: str = "en",
#     pause_time: float = 2.0,
#     scrape_timeout: int = 15,  # Add timeout for scraping
#     include_tables: bool = False,
#     favour_precision: bool = True,
# ) -> list[dict[str, Optional[str]]]:  # Return list of dicts, text can be None
#     """
#     Asynchronously queries the web and scrapes results concurrently.

#     Args:
#         query (str): The search term.
#         num_results (int): Max number of search results to retrieve URLs for.
#         lang (str): Language code for the search.
#         pause_time (float): Pause between Google search requests (sync part).
#         scrape_timeout (int): Timeout in seconds for each website scraping attempt.
#         include_tables (bool): Whether to include table text during scraping.
#         favour_precision (bool): Prioritize precision in text extraction.

#     Returns:
#         List[Dict[str, Optional[str]]]: A list of dictionaries, each containing:
#             'url': The URL of the search result.
#             'website_text': The extracted text (str) or None if scraping failed.
#     """
#     # Step 1: Perform the Google search (synchronous code run in a thread)
#     # Use asyncio.to_thread to run the blocking search function without blocking the event loop
#     try:
#         urls = await asyncio.to_thread(
#             perform_google_search, query, num_results, lang, pause_time
#         )
#     except Exception as e:
#         logging.exception(f"Error running Google search in thread: {e}")
#         urls = []

#     if not urls:
#         logging.info("No URLs found or search failed.")
#         return []

#     logging.info(f"\nStarting concurrent scraping for {len(urls)} URLs...")
#     results = []
#     # Create a single aiohttp session to be reused for all requests
#     async with aiohttp.ClientSession() as session:
#         # Create a list of tasks for concurrent scraping
#         tasks = [
#             extract_main_text_from_url(
#                 url,
#                 session,
#                 timeout=scrape_timeout,
#                 include_tables=include_tables,
#                 favour_precision=favour_precision,
#             )
#             for url in urls
#         ]

#         # Run tasks concurrently and gather results
#         # return_exceptions=True ensures that if one task fails, others continue,
#         # and the exception object is returned in place of the result.
#         scraped_texts_or_errors = await asyncio.gather(*tasks, return_exceptions=True)

#     # Step 3: Combine URLs with scraped text (or error indicators)
#     logging.info("\nScraping finished. Processing results...")
#     for i, url in enumerate(urls):
#         site_data = {"url": url}
#         result = scraped_texts_or_errors[i]

#         if isinstance(result, Exception):
#             logging.info(f"Failed to scrape {url}: {type(result).__name__} - {result}")
#             site_data["website_text"] = None  # Indicate failure with None
#         elif result is None:
#             logging.info(f"Scraping completed for {url}, but no text was extracted.")
#             site_data["website_text"] = None  # Indicate no text extracted with None
#         else:
#             logging.info(f"Successfully processed {url}")
#             site_data["website_text"] = result  # Assign the extracted text

#         results.append(site_data)

#     logging.info(f"\nProcessed {len(results)} URLs.")
#     return results


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
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )
        if result and result.text is not None:

            return result.text
