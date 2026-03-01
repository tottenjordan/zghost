import os
import logging

logging.basicConfig(level=logging.INFO)

import googleapiclient.discovery
from google.cloud import bigquery
from google.adk.tools import ToolContext

from ...shared_libraries.config import config
from ...shared_libraries.secrets import access_secret_version


# ========================
# clients — lazily initialized (Agent Engine injects env vars after import)
# ========================
_youtube_client = None
_bq_client = None


def get_youtube_client():
    global _youtube_client
    if _youtube_client is None:
        yt_secret_id = os.environ.get("YT_SECRET_MNGR_NAME")
        if not yt_secret_id:
            raise Exception("YT_SECRET_MNGR_NAME environment variable not set")
        api_key = access_secret_version(secret_id=yt_secret_id, version_id="1")
        _youtube_client = googleapiclient.discovery.build(
            serviceName="youtube", version="v3", developerKey=api_key
        )
    return _youtube_client


def get_bq_client():
    global _bq_client
    if _bq_client is None:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise Exception("GOOGLE_CLOUD_PROJECT environment variable not set")
        _bq_client = bigquery.Client(project=project)
    return _bq_client


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
    region_code: str = "US",
    max_results: int = config.max_results_yt_trends,
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

    request = get_youtube_client().videos().list(
        part="snippet,contentDetails",  # statistics
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    )
    trend_response = request.execute()
    # return trend_response

    # TODO: only return select fields
    trend_dict = {}
    i = 1
    for video in trend_response["items"]:
        row_name = f"row_{i}"
        trend_dict.update(
            {
                row_name: {
                    "videoId": video["id"],
                    "videoTitle": video["snippet"]["title"],
                    # 'videoDescription': video['snippet']['description'],
                    "duration": video["contentDetails"]["duration"],
                    "videoURL": f"https://www.youtube.com/watch?v={video['id']}",
                }
            }
        )
        i += 1
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
    max_date = get_bq_client().query(query).to_dataframe()
    return max_date.iloc[0][0].strftime("%m/%d/%Y")


def get_daily_gtrends(today_date: str = None) -> dict:
    """
    Retrieves the top 25 Google Search Trends (term, rank, refresh_date).

    Args:
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
        df_t = get_bq_client().query(query).to_dataframe()
        df_t.index += 1
        df_t["rank"] = df_t.index
        df_t = df_t.drop("x", axis=1)
        new_order = ["term", "rank", "refresh_date"]
        df_t = df_t[new_order]
        markdown_string = df_t.to_markdown(index=True)
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

    return {
        "status": "ok",
        f"markdown_table": markdown_string,
    }


async def auto_select_trends(
    num_search_trends: int,
    num_yt_trends: int,
    tool_context: ToolContext,
) -> dict:
    """
    Automatically select brand-safe trends using Gemini with Google Search grounding.

    Fetches available trends from Google Search and YouTube, evaluates each for brand safety
    using Gemini with real-time Google Search context, filters unsafe ones, scores by relevance
    to the campaign brand/product/audience, and saves the selections to session state.

    Args:
        num_search_trends: Number of Google Search trends to select.
        num_yt_trends: Number of YouTube trends to select.
        tool_context: The ADK tool context (provides session state).

    Returns:
        dict with selected trends, safety results, and reasoning.
    """
    from google import genai
    from google.genai import types
    from datetime import datetime
    import json as json_mod

    brand = tool_context.state.get("brand", "")
    target_product = tool_context.state.get("target_product", "")
    target_audience = tool_context.state.get("target_audience", "")
    key_selling_points = tool_context.state.get("key_selling_points", "")

    # 1. Fetch available trends
    search_result = get_daily_gtrends()
    yt_result = get_youtube_trends()

    # Parse search trends into list of dicts
    search_trends = []
    if search_result.get("status") == "ok" and search_result.get("markdown_table"):
        for line in search_result["markdown_table"].split("\n"):
            line = line.strip()
            if not line.startswith("|") or "term" in line.lower() or line.startswith("|---"):
                continue
            if all(c in "|- :" for c in line):
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 3:
                try:
                    rank = int(cells[0])
                    term = cells[1]
                    refresh_date = str(cells[3]) if len(cells) > 3 else ""
                    search_trends.append({
                        "title": term,
                        "rank": rank,
                        "refresh_date": refresh_date,
                        "source": "google_search",
                    })
                except (ValueError, IndexError):
                    continue

    # Parse YouTube trends
    yt_trends = []
    for key, video in yt_result.items():
        if not key.startswith("row_"):
            continue
        row_num = int(key.split("_")[1])
        yt_trends.append({
            "title": video.get("videoTitle", "Untitled"),
            "rank": row_num,
            "videoUrl": video.get("videoURL", ""),
            "duration": video.get("duration", ""),
            "source": "youtube",
        })

    if not search_trends and not yt_trends:
        return {"status": "error", "error_message": "No trends available from either source."}

    # 2. Run Gemini safety check with Google Search grounding
    all_trends = search_trends + yt_trends
    trend_list = "\n".join(
        f"- {t['title']} (Source: {t['source']})" for t in all_trends
    )

    today = datetime.utcnow().strftime("%B %d, %Y")
    brand_context = f"Brand: {brand}" if brand else "Brand: not specified"
    audience_context = f"Target audience: {target_audience}" if target_audience else ""

    prompt = f"""You are a brand safety analyst. Evaluate each trend below for appropriateness as a marketing campaign topic.

Use Google Search to look up each trend's current context before evaluating brand safety. Consider what the trend actually refers to right now, not just the title.

Today's date: {today}
{brand_context}
{audience_context}
Safety level: standard

TRENDS TO EVALUATE:
{trend_list}

For EACH trend, assess:
1. Is it brand-safe for advertising?
2. Is it contextually appropriate given today's date?
3. Would associating a brand with this trend pose reputational risk?

Respond in JSON format (no markdown fencing):
{{
  "results": [
    {{
      "trend_title": "exact trend title",
      "safe": true/false,
      "risk_level": "safe" | "caution" | "unsafe",
      "reason": "brief explanation",
      "categories": ["list of flagged categories if any"]
    }}
  ]
}}

IMPORTANT: Core safety rules that CANNOT be overridden:
- Violence, hate speech, adult/sexual content → always "unsafe"
- Active tragedies, mass casualty events → always "unsafe"
- Extreme political polarization → always "unsafe"
"""

    client = genai.Client(vertexai=True)
    safety_results = []
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[: raw_text.rfind("```")]
        parsed = json_mod.loads(raw_text)
        safety_results = parsed.get("results", [])
    except Exception as e:
        logging.error("Safety check failed in auto_select_trends: %s", e)
        # If safety check fails, proceed without filtering
        safety_results = [{"trend_title": t["title"], "safe": True, "risk_level": "safe", "reason": "Safety check unavailable"} for t in all_trends]

    # Build safety lookup
    safety_by_title = {r["trend_title"]: r for r in safety_results}

    # 3. Filter out unsafe trends
    safe_search = [t for t in search_trends if safety_by_title.get(t["title"], {}).get("safe", True)]
    safe_yt = [t for t in yt_trends if safety_by_title.get(t["title"], {}).get("safe", True)]

    # 4. Score by keyword relevance
    keywords = set()
    for val in [brand, target_product, target_audience, key_selling_points]:
        if val:
            keywords.update(w.lower() for w in val.split() if len(w) > 2)

    def relevance_score(trend):
        title_lower = trend["title"].lower()
        if not keywords:
            return 0
        return sum(1 for kw in keywords if kw in title_lower) / len(keywords)

    safe_search.sort(key=relevance_score, reverse=True)
    safe_yt.sort(key=relevance_score, reverse=True)

    # 5. Select requested count
    selected_search = safe_search[:num_search_trends]
    selected_yt = safe_yt[:num_yt_trends]

    # 6. Save to session state
    for trend in selected_search:
        await save_search_trends_to_session_state(
            {
                "trend_title": trend["title"],
                "trend_rank": trend["rank"],
                "trend_refresh_date": trend.get("refresh_date", ""),
            },
            tool_context,
        )

    for trend in selected_yt:
        await save_yt_trends_to_session_state(
            {
                "video_title": trend["title"],
                "video_duration": trend.get("duration", ""),
                "video_url": trend.get("videoUrl", ""),
            },
            tool_context,
        )

    # Build reasoning
    unsafe_count = sum(1 for r in safety_results if not r.get("safe", True))
    reasoning = (
        f"Evaluated {len(search_trends)} search and {len(yt_trends)} YouTube trends. "
        + (f"Filtered {unsafe_count} unsafe trend(s) via Gemini + Google Search grounding. " if unsafe_count else "")
        + f"Selected {len(selected_search)} search and {len(selected_yt)} YouTube trends"
        + (f" optimized for '{brand}'." if brand else ".")
    )

    return {
        "status": "ok",
        "selected_search_trends": selected_search,
        "selected_yt_trends": selected_yt,
        "safety_results": safety_results,
        "reasoning": reasoning,
    }
