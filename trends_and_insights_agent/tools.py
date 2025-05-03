import os
import uuid
import logging
from .prompts import united_insights_prompt
from pydantic import BaseModel
from google.adk.agents import Agent

logging.basicConfig(level=logging.INFO)

try:
    # The library is called 'googlesearch', but installed via 'googlesearch-python'
    from googlesearch import search

except ImportError:
    logging.exception("Could not import the 'googlesearch' library.")
    logging.exception("Please install it first using: pip install googlesearch-python")
    search = None  # Set search to None so the script doesn't crash immediately

import asyncio
import aiohttp
import trafilatura
import pandas as pd
from typing import Optional  # , AsyncGenerator

from google.genai import types
from google.genai import Client
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from google.cloud import secretmanager as sm
import googleapiclient.discovery

from .common_agents.marketing_guide_data_generator.agent import (
    campaign_guide_data_generation_agent,
)

# clients
sm_client = sm.SecretManagerServiceClient()
SECRET_ID = f'projects/{os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER")}/secrets/{os.environ.get("YT_SECRET_MNGR_NAME")}'  # yt-data-api
SECRET_VERSION = "{}/versions/1".format(SECRET_ID)
response = sm_client.access_secret_version(request={"name": SECRET_VERSION})
YOUTUBE_DATA_API_KEY = response.payload.data.decode("UTF-8")
youtube_client = googleapiclient.discovery.build(
    serviceName="youtube", version="v3", developerKey=YOUTUBE_DATA_API_KEY
)

# Only Vertex AI supports image generation for now.
client = Client()


async def call_guide_generation_agent(
    question: str, tool_context: ToolContext, file_path: str
):
    """Tool to call the campaign guide data generation agent.
    Question: The question to ask the agent.
    tool_context: The tool context.
    file_path: The path to the file to load, this is the pdf report.
    """
    agent_tool = AgentTool(campaign_guide_data_generation_agent)
    agent_name = tool_context.agent_name
    artifact_part = types.Part(text=file_path)

    # TODO: support user upload artifacts
    # tool_context.save_artifact("campaign_guide.pdf", artifact_part)

    campaign_guide_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["campaign_guide"] = campaign_guide_output
    return campaign_guide_output


# ========================
# search tools
# ========================
def perform_google_search(
    query: str,
    num_results: int = 10,
    lang: str = "en",
    pause_time: float = 2.0,
) -> list:
    # ) -> AsyncGenerator[list, None]:
    """
    Performs a Google search for a given query using the googlesearch-python library.

    Args:
        query (str): The search term.
        num_results (int): The desired number of search results to retrieve.
        lang (str): The language code for the search (e.g., 'en', 'es').
        pause_time (float): Seconds to pause between HTTP requests to avoid blocking.

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


async def extract_main_text_from_url(
    url: str,
    session: aiohttp.ClientSession,  # Pass the session for reuse
    timeout: int = 15,
    include_tables: bool = False,
    favour_precision: bool = True,
) -> Optional[str]:  # Returns a single string or None
    """
    Fetches a webpage asynchronously and extracts the main textual content using trafilatura.

    Args:
        url (str): The URL of the webpage to scrape.
        session (aiohttp.ClientSession): The aiohttp session to use for requests.
        timeout (int): Max time in seconds to wait for the server response.
        include_tables (bool): Whether to include text found within HTML tables.
        favour_precision (bool): If True, prioritizes accuracy over recall.

    Returns:
        Optional[str]: The extracted main text content, or None if an error occurs.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    extracted_text = None
    logging.info(f"Attempting to fetch URL: {url}")

    try:
        async with session.get(
            url, headers=headers, timeout=timeout, allow_redirects=True
        ) as response:
            # Raise an HTTPError for bad responses (4xx or 5xx)
            # aiohttp doesn't raise by default like requests, so we check status
            if response.status >= 400:
                logging.info(f"HTTP Error {response.status} for URL {url}")
                # Optionally raise an exception or just return None
                # response.raise_for_status() # This would raise ClientResponseError
                return None  # Return None on client/server errors

            # Check content type (optional)
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                logging.info(
                    f"Warning: Content-Type for {url} is '{content_type}'. Extraction might be suboptimal."
                )

            # Read the response content as bytes (best for trafilatura)
            html_content = await response.read()

            # Run trafilatura extraction (potentially blocking, see note below)
            logging.info(f"Extracting main content from {url} using trafilatura...")
            # Note: trafilatura itself is synchronous CPU-bound code.
            # For *very* heavy pages or *many* concurrent tasks on a limited machine,
            # you *might* consider running this part in a thread pool executor too,
            # using loop.run_in_executor(None, trafilatura.extract, ...),
            # but often the network I/O is the main bottleneck, so direct call is fine.
            extracted_text = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=include_tables,
                favor_precision=favour_precision,
                # target_language='en' # Optional
            )

            if not extracted_text and favour_precision:
                logging.info(
                    f"Precision mode yielded no text for {url}, trying recall mode..."
                )
                extracted_text = trafilatura.extract(
                    html_content,
                    include_comments=False,
                    include_tables=include_tables,
                    favor_recall=True,  # Switch to favouring recall
                )

            if extracted_text:
                logging.info(
                    f"Successfully extracted content from {url} (approx. {len(extracted_text)} chars)."
                )
            else:
                # Check if original response text had *any* text
                try:
                    # Try decoding for the check, ignore errors
                    page_text = html_content.decode(errors="ignore")
                    if page_text and len(page_text.strip()) > 0:
                        logging.info(
                            f"Trafilatura could not extract main content from {url}, though the page was fetched."
                        )
                    else:
                        logging.info(
                            f"The fetched page {url} appears to have no text content."
                        )
                except Exception:  # Guard against decoding errors just for the print
                    logging.exception(
                        f"Trafilatura could not extract main content from {url} (and checking raw text failed)."
                    )

                extracted_text = None  # Ensure None is returned if extraction fails

    except aiohttp.ClientError as e:
        # Handles client-side exceptions like connection errors, timeouts
        logging.exception(f"Aiohttp client error fetching URL {url}: {e}")
        extracted_text = None
    except asyncio.TimeoutError:
        logging.exception(f"Timeout error fetching URL {url} after {timeout} seconds.")
        extracted_text = None
    except Exception as e:
        # Catch potential unexpected errors during extraction or other issues
        logging.exception(
            f"An unexpected error occurred for URL {url}: {type(e).__name__} - {e}"
        )
        extracted_text = None

    # No yield needed, just return the final result for this URL
    return extracted_text


async def query_web(
    query: str,
    num_results: int = 10,
    lang: str = "en",
    pause_time: float = 2.0,
    scrape_timeout: int = 15,  # Add timeout for scraping
    include_tables: bool = False,
    favour_precision: bool = True,
) -> list[dict[str, Optional[str]]]:  # Return list of dicts, text can be None
    """
    Asynchronously queries the web and scrapes results concurrently.

    Args:
        query (str): The search term.
        num_results (int): Max number of search results to retrieve URLs for.
        lang (str): Language code for the search.
        pause_time (float): Pause between Google search requests (sync part).
        scrape_timeout (int): Timeout in seconds for each website scraping attempt.
        include_tables (bool): Whether to include table text during scraping.
        favour_precision (bool): Prioritize precision in text extraction.

    Returns:
        List[Dict[str, Optional[str]]]: A list of dictionaries, each containing:
            'url': The URL of the search result.
            'website_text': The extracted text (str) or None if scraping failed.
    """
    # Step 1: Perform the Google search (synchronous code run in a thread)
    # Use asyncio.to_thread to run the blocking search function without blocking the event loop
    try:
        urls = await asyncio.to_thread(
            perform_google_search, query, num_results, lang, pause_time
        )
    except Exception as e:
        logging.exception(f"Error running Google search in thread: {e}")
        urls = []

    if not urls:
        logging.info("No URLs found or search failed.")
        return []

    logging.info(f"\nStarting concurrent scraping for {len(urls)} URLs...")
    results = []
    # Create a single aiohttp session to be reused for all requests
    async with aiohttp.ClientSession() as session:
        # Create a list of tasks for concurrent scraping
        tasks = [
            extract_main_text_from_url(
                url,
                session,
                timeout=scrape_timeout,
                include_tables=include_tables,
                favour_precision=favour_precision,
            )
            for url in urls
        ]

        # Run tasks concurrently and gather results
        # return_exceptions=True ensures that if one task fails, others continue,
        # and the exception object is returned in place of the result.
        scraped_texts_or_errors = await asyncio.gather(*tasks, return_exceptions=True)

    # Step 3: Combine URLs with scraped text (or error indicators)
    logging.info("\nScraping finished. Processing results...")
    for i, url in enumerate(urls):
        site_data = {"url": url}
        result = scraped_texts_or_errors[i]

        if isinstance(result, Exception):
            logging.info(f"Failed to scrape {url}: {type(result).__name__} - {result}")
            site_data["website_text"] = None  # Indicate failure with None
        elif result is None:
            logging.info(f"Scraping completed for {url}, but no text was extracted.")
            site_data["website_text"] = None  # Indicate no text extracted with None
        else:
            logging.info(f"Successfully processed {url}")
            site_data["website_text"] = result  # Assign the extracted text

        results.append(site_data)

    logging.info(f"\nProcessed {len(results)} URLs.")
    return results


###
# YT
###


def query_youtube_api(
    query: str,
    region_code: str,
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
        region_code (str): selects a video chart available in the specified region.
            Values are ISO 3166-1 alpha-2 country codes. For example, the region_code for the United Kingdom would be 'GB',
            whereas 'US' would represent The United States.
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
        regionCode=region_code,
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


def analyze_youtube_videos(
    prompt: str,
    youtube_url: str,
) -> str:
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

        model = "gemini-2.0-flash-001"
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt), video],
            )
        ]
        result = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                # system_instruction=youtube_analysis_prompt,
            ),
        )
        return result.text


class Insight(BaseModel):
    "Data model for insights from Google and Youtube research."

    insight_title: str
    insight_text: str
    insight_urls: str
    key_entities: str
    key_relationships: str
    key_audiences: str
    key_product_insights: str


class Insights(BaseModel):
    "Data model for insights from Google and Youtube research."

    insights: list[Insight]


# agent tool to capture insights
insights_generator_agent = Agent(
    model="gemini-2.0-flash-001",
    name="insights_generator_agent",
    instruction=united_insights_prompt,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    output_schema=Insights,
    output_key="insights",
)


async def call_insights_generation_agent(question: str, tool_context: ToolContext):
    """
    Tool to call the insights generation agent. Use this tool to update the list of insights in the agent's state.
    Question: The question to ask the agent, use the tool_context to extract the following schema:
        insight_title: str -> Come up with a unique title for the insight
        insight_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
        insight_urls: str -> Get the url from the `query_youtube_api` tool or `query_web` tool
        key_entities: str -> Develop entities from the source to create a graph (see relations)
        key_relationships: str -> Create relationships between the key_entities to create a graph
        key_audiences: str -> Considering the guide, how does this insight intersect with the audience?
        key_product_insights: str -> Considering the guide, how does this insight intersect with the product?
    tool_context: The tool context.
    """

    agent_tool = AgentTool(insights_generator_agent)
    existing_insights = tool_context.state.get("insights")
    insights = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    logging.info(f"Insights: {insights}")
    logging.info(f"Existing insights: {existing_insights}")
    if existing_insights is not {'insights': []}:
        insights["insights"].extend(
            existing_insights["insights"]
        )  # TODO: Validate how to keep a history of trends & insights
    logging.info(f"Final insights: {insights}")
    tool_context.state["insights"] = insights
    return {"status": "ok"}
