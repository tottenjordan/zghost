# First, you need to install the library:
# pip install googlesearch-python[[5](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqALo5ddbZqNitMjLrYkz4YeJXzELaDFdSJ0Iv3X9WYFVW6uZEVAcrgdyC6zNLXsLMh2K1zu6H_OfC1FSKvtLtzROwAADGamnvGdXM0wIH8Hy4KMOHVmGE0mDnAORUQO-LA94i5m-ImKXi4-XmWkurkOywbipWViMoHDvqku-RDN_4kpqlfcoAULZm4YYGp1bOeuDxgWJEl3V_aF42ARLUV9pBv5tpYTYidtH5_9PuzjnYk-iY7PT_Tdoh-ViV3WlJt3Tq-19XjF0xA==)]

try:
    # The library is called 'googlesearch', but installed via 'googlesearch-python'
    from googlesearch import search

except ImportError:
    print("Could not import the 'googlesearch' library.")
    print("Please install it first using: pip install googlesearch-python")
    search = None  # Set search to None so the script doesn't crash immediately

import requests
import trafilatura
from requests.exceptions import RequestException
from google.adk.tools import ToolContext
from google.genai import types
import uuid
from google import genai
from .prompts import youtube_analysis_prompt
from typing import Any
from google.genai import types

client = genai.Client()


def analyze_youtube_videos(
    youtube_url: str,
    # tool_context: "ToolContext",
) -> str:
    """
    Analyzes youtube videos from a list of search results.
    Args:
        search_results_urls (list[str]): The list of urls to check for youtube.com
    Returns:
        Results from the youtube video analysis prompt.
    """

    if "youtube.com" not in youtube_url:
        return "Not a valid youtube URL"
    else:
        video1 = types.Part.from_uri(
            file_uri=youtube_url,
            mime_type="video/*",
        )

        model = "gemini-2.0-flash-001"
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=youtube_analysis_prompt), video1],
            )
        ]
        result = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )
        return result.text

# def save_yt_artifacts_from_search(
#     search_results_urls: list[str], tool_context: "ToolContext"
# ):
#     """
#     Saves youtube artifacts from search results.
#     Args:
#         search_results_urls (list[str]): The list of urls to check for youtube.com
#         tool_context (ToolContext): The tool context.
#     Returns:
#         None
#     """
#     for url in search_results_urls:
#         if "youtube.com" in url:
#             video_part = types.Part.from_uri(
#                 file_uri=url,
#                 mime_type="video/*",
#             )
#             filename = uuid.uuid4()
#             tool_context.save_artifact(
#                 f"{filename}.png",
#                 video_part,
#             )


async def perform_google_search(
    query: str,
    # tool_context: "ToolContext",
    num_results: int = 10,
    lang: str = "en",
    pause_time: float = 2.0,
):
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
        print("Googlesearch library not available. Cannot perform search.")
        return []

    search_results_urls = []
    print(f"Searching Google for: '{query}' (up to {num_results} results)...")
    try:
        # The search function returns a generator. We convert it to a list.[[1](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAIt0WzakIytkvxX-NyLXvi8MeY_Lt0gOuYicrDUrmlo-oMJU5YQyD8tzXvLuLEhWcYU9l5rdXcKddjNmU0AEb2_LVzo3sGqCr7_xnWMkqIUtpuW9_rohiniNpWh0CQoxZKz1tXlOg==)]
        # 'stop=num_results' ensures we try to fetch exactly that many.
        # 'pause' helps avoid getting temporarily blocked by Google.
        results_generator = search(
            query, num_results=num_results, lang=lang, sleep_interval=pause_time
        )
        search_results_urls = list(results_generator)

        print(f"Found {len(search_results_urls)} results.")

    except Exception as e:
        print(f"An error occurred during the Google search: {e}")
        print("This might be due to network issues or Google blocking the request.")
        print("Try increasing the 'pause_time' or searching less frequently.")

    return search_results_urls


# # --- Example Usage ---
# # Decide on the search term based on the findings:
# # search_term_adk = "Google Agent Development Kit" # For the ADK framework [4, 11]
# search_term_sdk = (
#     "Google Gemini AI SDK python"  # For the core Gemini API library [1, 3, 9]
# )
# search_term_general = "What is the latest Gemini model?"  # For a general search

# # Choose which term to use for the example:
# # Let's search for the ADK as originally requested, using the more specific name
# chosen_search_term = "Google Agent Development Kit"

# # Perform the search
# results = perform_google_search(chosen_search_term, num_results=5)

# # Print the results
# if results:
#     print("\n--- Search Results URLs ---")
#     for i, url in enumerate(results):
#         print(f"{i+1}: {url}")
# else:
#     print("\nNo results were returned or an error occurred.")


def extract_main_text_from_url(
    url: str,
    timeout: int = 15,
    include_tables: bool = False,
    favour_precision: bool = True,
):
    """
    Fetches a webpage and extracts the main textual content using trafilatura.

    This aims to remove boilerplate (menus, ads, footers) to get text suitable
    for processing by language models like Gemini.

    Args:
        url (str): The URL of the webpage to scrape.
        timeout (int): Max time in seconds to wait for the server response.
        include_tables (bool): Whether to include text found within HTML tables.
        favour_precision (bool): If True, prioritizes accuracy over recall
                                 (less text, potentially higher quality).
                                 If False (favour_recall), tries to get more text.

    Returns:
        str: The extracted main text content as a single string, or None if
             an error occurs or content extraction fails significantly.
    """
    # Using a realistic User-Agent can help avoid being blocked by some websites
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    extracted_text = None
    print(f"Attempting to fetch URL: {url}")

    try:
        # Fetch the HTML content
        response = requests.get(
            url, headers=headers, timeout=timeout, allow_redirects=True
        )
        # Raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()

        # Optional: Check content type (trafilatura often handles non-HTML gracefully)
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type:
            print(
                f"Warning: Content-Type is '{content_type}'. Extraction might be suboptimal."
            )
            # You could choose to return None here if you strictly require HTML

        # Use trafilatura to extract the main content from the fetched HTML
        # response.content passes the raw bytes, letting trafilatura handle encoding
        print("Extracting main content using trafilatura...")
        extracted_text = trafilatura.extract(
            response.content,
            include_comments=False,  # Don't include HTML comments
            include_tables=include_tables,  # Include table text if requested
            favor_precision=favour_precision,
            # target_language='en' # Optional: Specify language code if known e.g., 'en', 'de'
            # Helps if encoding/language detection is tricky
        )

        if not extracted_text and favour_precision:
            # If precision mode yielded nothing, try recall mode as a fallback
            print("Precision mode yielded no text, trying recall mode...")
            extracted_text = trafilatura.extract(
                response.content,
                include_comments=False,
                include_tables=include_tables,
                favor_recall=True,  # Switch to favouring recall
            )

        if extracted_text:
            print(
                f"Successfully extracted content (approx. {len(extracted_text)} chars)."
            )
        else:
            # Check if original response text had *any* text, even if not extracted
            if response.text and len(response.text.strip()) > 0:
                print(
                    "Trafilatura could not extract main content, though the page was fetched."
                )
            else:
                print("The fetched page appears to have no text content.")
            extracted_text = None  # Ensure None is returned if extraction fails

    except RequestException as e:
        print(f"Error fetching or processing URL {url}: {e}")
        extracted_text = None  # Ensure None on network/HTTP error
    except Exception as e:
        # Catch potential unexpected errors during extraction
        print(f"An unexpected error occurred: {e}")
        extracted_text = None

    return extracted_text
