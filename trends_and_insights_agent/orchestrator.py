"""LlmAgent orchestrator for the campaign pipeline.

Replaces the BaseAgent state machine with a single LlmAgent that uses 7 tool
functions to run the pipeline. The LLM decides which tool to call based on
session state and its instruction.

Pipeline stages (via tools):
  gather_trends     -> deterministic (BigQuery + YouTube API, no LLM)
  run_research      -> direct model call (gemini-3-flash-preview)
  run_ad_creative   -> ad_creative_agent sub-agent
  generate_images   -> deterministic SDK (Imagen 4) + Gecko scoring
  generate_commercial -> deterministic SDK (Veo 3.1)
  run_focus_group   -> focus_group_evaluator_agent sub-agent
  save_report       -> save_final_report_tool (direct call, no LLM)
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from google.genai import types
from google.genai.types import GenerateImagesConfig, GenerateVideosConfig
from google.adk.tools import ToolContext

from .common_agents.ad_content_generator.tools import save_final_report_tool
from .shared_libraries.config import config
from .shared_libraries.utils import upload_blob_to_gcs, download_blob
from .shared_libraries.fidelity_eval.gecko import evaluate as gecko_evaluate

logger = logging.getLogger("google_adk." + __name__)

# ---------------------------------------------------------------------------
# GCS Write-Through Cache (AE state persistence fix)
# ---------------------------------------------------------------------------
# On Agent Engine, tool_context.state writes are lost when AE waves timeout
# before the function_response event is persisted. This write-through cache
# saves critical state to GCS, and _load_session_state recovers it each wave.
# ---------------------------------------------------------------------------

_GCS_STATE_KEYS = [
    "combined_final_cited_report",
    "ad_creative_output",
    "commercial_artifact",
    "focus_group_evaluation",
    "final_select_ad_copies",
    "final_select_visual_concepts",
    "final_select_vis_concepts",
]


def _gcs_state_write(key: str, value, gcs_folder: str):
    """Write a state value to GCS as a side-channel for cross-wave recovery."""
    import json as _json
    if not gcs_folder:
        return
    try:
        bucket = os.getenv("BUCKET", "gs://zghost-media-center")
        blob_name = f"{gcs_folder}/state/{key}.json"
        data = _json.dumps(value, default=str) if not isinstance(value, str) else value
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(data)
            tmp_path = f.name
        try:
            upload_blob_to_gcs(source_file_name=tmp_path, destination_blob_name=blob_name)
            logger.info(f"[gcs_state] Wrote {key} ({len(data)} chars) to gs://.../{blob_name}")
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        logger.warning(f"[gcs_state] Write failed for {key}: {e}")


def _gcs_state_read(key: str, gcs_folder: str):
    """Read a state value from GCS side-channel."""
    import json as _json
    if not gcs_folder:
        return None
    try:
        bucket = os.getenv("BUCKET", "gs://zghost-media-center")
        bucket_name = bucket.replace("gs://", "")
        blob_name = f"{gcs_folder}/state/{key}.json"
        data = download_blob(bucket_name=bucket_name, source_blob_name=blob_name)
        if data:
            text = data.decode('utf-8') if isinstance(data, bytes) else data
            try:
                return _json.loads(text)
            except _json.JSONDecodeError:
                return text if len(text) > 10 else None
    except Exception:
        pass
    return None


def gcs_state_recover(state) -> int:
    """Recover lost tool outputs from GCS. Called by _load_session_state each wave.

    Returns the number of keys recovered.
    """
    gcs_folder = state.get("gcs_folder", "")
    if not gcs_folder:
        return 0
    recovered = 0
    for key in _GCS_STATE_KEYS:
        current = state.get(key)
        # Skip if state already has meaningful data
        if current and (isinstance(current, str) and len(current) > 50):
            continue
        if current and isinstance(current, dict) and any(
            isinstance(v, list) and len(v) > 0 for v in current.values()
        ):
            continue
        cached = _gcs_state_read(key, gcs_folder)
        if cached:
            is_valid = False
            if isinstance(cached, str) and len(cached) > 50:
                is_valid = True
            elif isinstance(cached, dict):
                is_valid = True
            if is_valid:
                state[key] = cached
                recovered += 1
                logger.info(f"[gcs_state] Recovered {key} from GCS ({type(cached).__name__})")
    return recovered


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_CREATIVE_ATTEMPTS = 15
AV_STUDIO_MAX_RUNS = 5
AE_WAVE_POLL_BUDGET = 55  # seconds to poll Veo within a single AE wave
GECKO_THRESHOLD = 0.7
MAX_IMAGES = 3
MAX_IMG_RETRIES = 5

# ---------------------------------------------------------------------------
# Cached media gen client (us-central1 for Imagen/Veo, NOT "global")
# ---------------------------------------------------------------------------
_media_client = None


def _get_media_client():
    global _media_client
    if _media_client is None:
        _media_client = genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "wortz-project-352116"),
            location="us-central1",
        )
    return _media_client


# ---------------------------------------------------------------------------
# Helper: parse search trends from markdown table
# ---------------------------------------------------------------------------
def _parse_search_trends(gtrends_result: dict) -> list[dict]:
    if gtrends_result.get("status") != "ok":
        return []
    md_table = gtrends_result.get("markdown_table", "")
    if not md_table:
        return []
    lines = [l.strip() for l in md_table.strip().split("\n") if l.strip()]
    if len(lines) < 3:
        return []
    trends = []
    for row in lines[2:]:
        cells = [c.strip() for c in row.split("|") if c.strip()]
        if len(cells) < 4:
            continue
        date_str = str(cells[3])
        if len(date_str) == 10 and date_str[4] == "-":
            parts = date_str.split("-")
            date_str = f"{parts[1]}/{parts[2]}/{parts[0]}"
        trends.append({
            "trend_title": cells[1],
            "trend_rank": int(cells[2]),
            "trend_refresh_date": date_str,
        })
    return trends


# ---------------------------------------------------------------------------
# Helper: extract trend context from state
# ---------------------------------------------------------------------------
def _get_trend_context(state: dict) -> str:
    search_trends = state.get("target_search_trends", {})
    search_title = ""
    if isinstance(search_trends, dict):
        st_list = search_trends.get("target_search_trends", [])
        if st_list:
            search_title = st_list[0].get("title", st_list[0].get("trend_title", "")) if isinstance(st_list[0], dict) else str(st_list[0])
    yt_trends = state.get("target_yt_trends", {})
    yt_title = ""
    if isinstance(yt_trends, dict):
        yt_list = yt_trends.get("target_yt_trends", [])
        if yt_list:
            yt_title = yt_list[0].get("title", yt_list[0].get("video_title", "")) if isinstance(yt_list[0], dict) else str(yt_list[0])
    trend_context = ""
    if search_title:
        trend_context += f'the "{search_title}" trend'
    if yt_title:
        trend_context += f' and the "{yt_title}" YouTube trend' if trend_context else f'the "{yt_title}" YouTube trend'
    return trend_context


def _has_trends(trends) -> bool:
    if not trends:
        return False
    if isinstance(trends, dict):
        for v in trends.values():
            if isinstance(v, list) and len(v) > 0:
                return True
        return False
    if isinstance(trends, list):
        return len(trends) > 0
    return bool(trends)


# ===================================================================
# TOOL 1: gather_trends
# ===================================================================
def gather_trends(tool_context: ToolContext) -> dict:
    """Fetch real-time Google Search trends and YouTube trends for the campaign.

    Call this FIRST in the pipeline. Fetches trends IN PARALLEL, caches them
    in both session state and Memory Bank (1hr TTL).

    In autopilot mode: auto-selects the best trend based on keyword scoring.
    In interactive mode: returns the full trend tables for the user to pick from.
    After the user picks, call select_trend to save their choice.

    Returns a summary dict with trend tables and (in autopilot) auto-selections.
    """
    from .common_agents.trend_assistant.tools import get_daily_gtrends, get_youtube_trends
    import json as _json

    state = tool_context.state
    results = {"status": "ok", "search_trend": None, "youtube_trend": None}

    # --- Check Memory Bank cache first (1hr TTL) ---
    cached_search = _recall_cached_trends("google_trend", state)
    cached_yt = _recall_cached_trends("youtube_trend", state)

    gtrends_result = None
    yt_result = None

    if cached_search and cached_yt:
        logger.info("[gather_trends] Using Memory Bank cached trends (< 1hr old)")
        results["cache_hit"] = True
        all_trends = cached_search
        yt_list = cached_yt
    else:
        # --- Fire both API calls in parallel ---
        gtrends_error = None
        yt_error = None

        def _fetch_gtrends():
            return get_daily_gtrends()

        def _fetch_yt():
            return get_youtube_trends()

        with ThreadPoolExecutor(max_workers=2) as pool:
            g_future = pool.submit(_fetch_gtrends)
            y_future = pool.submit(_fetch_yt)

            try:
                gtrends_result = g_future.result(timeout=30)
            except Exception as e:
                gtrends_error = e

            try:
                yt_result = y_future.result(timeout=30)
            except Exception as e:
                yt_error = e

        # --- Parse Google Search Trends ---
        all_trends = []
        if gtrends_error:
            logger.warning(f"[gather_trends] Search trends failed: {gtrends_error}")
            results["search_error"] = str(gtrends_error)[:200]
        elif gtrends_result:
            all_trends = _parse_search_trends(gtrends_result)

        # --- Parse YouTube Trends ---
        yt_list = []
        if yt_error:
            logger.warning(f"[gather_trends] YouTube trends failed: {yt_error}")
            results["youtube_error"] = str(yt_error)[:200]
        elif yt_result:
            for key in sorted(yt_result.keys()):
                vid = yt_result[key]
                yt_list.append({
                    "video_title": vid.get("videoTitle", ""),
                    "video_duration": vid.get("duration", ""),
                    "video_url": vid.get("videoURL", ""),
                })

        # --- Save to Memory Bank with 1hr TTL ---
        if all_trends:
            _save_cached_trends("google_trend", all_trends, state)
        if yt_list:
            _save_cached_trends("youtube_trend", yt_list, state)

    # --- Cache in session state ---
    if all_trends:
        tool_context.state["_cached_search_trends"] = all_trends
    if yt_list:
        tool_context.state["_cached_yt_trends"] = yt_list

    # --- Build trend tables for display ---
    if all_trends:
        search_table = "| # | Trend | Rank | Date |\n|---|-------|------|------|\n"
        for i, t in enumerate(all_trends[:15]):
            search_table += f"| {i+1} | {t['trend_title']} | {t['trend_rank']} | {t['trend_refresh_date']} |\n"
        results["search_trends_table"] = search_table
        results["all_search_trends"] = [
            f"{i+1}. {t['trend_title']} (rank {t['trend_rank']})"
            for i, t in enumerate(all_trends[:15])
        ]

    if yt_list:
        yt_table = "| # | Title | Duration |\n|---|-------|----------|\n"
        for i, v in enumerate(yt_list[:15]):
            yt_table += f"| {i+1} | {v['video_title']} | {v['video_duration']} |\n"
        results["youtube_trends_table"] = yt_table
        results["all_youtube_trends"] = [
            f"{i+1}. {v['video_title']} ({v['video_duration']})"
            for i, v in enumerate(yt_list[:15])
        ]

    # Always interactive — present tables to user and wait for their pick via select_trend
    results["instructions"] = (
        "Present BOTH trend tables to the user in a clear format. "
        "Ask them to pick a Google Search trend number AND a YouTube trend number. "
        "Once they respond with their choices, call select_trend with those numbers. "
        "Do NOT proceed to run_research until the user has selected trends."
    )

    # Persist campaign metadata
    for key in ("brand", "target_product", "target_audience", "key_selling_points"):
        val = state.get(key, "")
        if val:
            tool_context.state[key] = val

    tool_context.state["commercial_duration"] = state.get("commercial_duration", 8)
    return results


def select_trend(search_trend_number: int, youtube_trend_number: int, tool_context: ToolContext) -> dict:
    """Save the user's trend selections from the gathered trends.

    Call this AFTER gather_trends when in interactive mode. The user picks
    trend numbers from the tables displayed by gather_trends.

    Args:
        search_trend_number: 1-based index of the Google Search trend to select.
        youtube_trend_number: 1-based index of the YouTube trend to select.

    Returns a dict confirming the selections.
    """
    state = tool_context.state
    cached_search = state.get("_cached_search_trends", [])
    cached_yt = state.get("_cached_yt_trends", [])

    results = {"status": "ok"}

    # Select search trend
    idx = search_trend_number - 1
    if 0 <= idx < len(cached_search):
        selected = cached_search[idx]
        tool_context.state["target_search_trends"] = {"target_search_trends": [selected]}
        results["search_trend"] = selected
    else:
        results["search_error"] = f"Invalid search trend number {search_trend_number} (1-{len(cached_search)})"

    # Select YouTube trend
    idx = youtube_trend_number - 1
    if 0 <= idx < len(cached_yt):
        selected = cached_yt[idx]
        tool_context.state["target_yt_trends"] = {"target_yt_trends": [selected]}
        results["youtube_trend"] = selected
    else:
        results["youtube_error"] = f"Invalid YouTube trend number {youtube_trend_number} (1-{len(cached_yt)})"

    return results


# ===================================================================
# Memory Bank trend caching helpers (1hr TTL)
# ===================================================================
_TREND_TTL_SECONDS = 3600  # 1 hour

def _save_cached_trends(scope: str, trends: list, state: dict):
    """Save trends to Memory Bank with scope and timestamp for TTL."""
    import json as _json
    try:
        import vertexai
        agent_engine_id = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
        if not agent_engine_id:
            return
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        project_number = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER")
        client = vertexai.Client(project=project, location="us-central1")
        resource_name = f"projects/{project_number}/locations/us-central1/reasoningEngines/{agent_engine_id}"
        # Store as a fact with timestamp for TTL checking
        fact = _json.dumps({
            "scope": scope,
            "timestamp": time.time(),
            "trends": trends[:15],  # Cap to avoid exceeding fact size limits
        })
        client.agent_engines.memories.generate(
            name=resource_name,
            direct_memories_source={"direct_memories": [{"fact": f"cached_{scope}: {fact}"}]},
            scope={"app_name": "trends_and_insights_agent", "cache_scope": scope},
            config={"wait_for_completion": False},
        )
        logger.info(f"[gather_trends] Saved {len(trends)} trends to Memory Bank scope={scope}")
    except Exception as e:
        logger.warning(f"[gather_trends] Memory Bank save failed for {scope}: {e}")


def _recall_cached_trends(scope: str, state: dict) -> list | None:
    """Recall cached trends from Memory Bank if within TTL."""
    import json as _json
    try:
        import vertexai
        agent_engine_id = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
        if not agent_engine_id:
            return None
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        project_number = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER")
        client = vertexai.Client(project=project, location="us-central1")
        resource_name = f"projects/{project_number}/locations/us-central1/reasoningEngines/{agent_engine_id}"
        results = list(client.agent_engines.memories.retrieve(
            name=resource_name,
            scope={"app_name": "trends_and_insights_agent", "cache_scope": scope},
            similarity_search_params={
                "search_query": f"cached_{scope} trends",
                "top_k": 3,
            },
        ))
        if not results:
            return None
        for mem in results:
            fact = getattr(mem, 'memory', mem)
            fact = getattr(fact, 'fact', str(fact)) if hasattr(fact, 'fact') else str(fact)
            if f"cached_{scope}:" in fact:
                json_str = fact.split(f"cached_{scope}:", 1)[1].strip()
                try:
                    data = _json.loads(json_str)
                    ts = data.get("timestamp", 0)
                    if time.time() - ts < _TREND_TTL_SECONDS:
                        logger.info(f"[gather_trends] Cache HIT for {scope} (age={int(time.time()-ts)}s)")
                        return data.get("trends", [])
                    else:
                        logger.info(f"[gather_trends] Cache EXPIRED for {scope} (age={int(time.time()-ts)}s)")
                except _json.JSONDecodeError:
                    continue
        return None
    except Exception as e:
        logger.warning(f"[gather_trends] Memory Bank recall failed for {scope}: {e}")
        return None


# ===================================================================
# TOOL 2: run_research
# ===================================================================
def run_research(tool_context: ToolContext) -> dict:
    """Generate a comprehensive marketing research report using the campaign context and trends.

    Call this AFTER gather_trends. Uses a direct Gemini model call to synthesize
    research from trends, YouTube analysis, and campaign context.

    Returns a dict with the research report text and its length.
    """
    state = tool_context.state
    brand = state.get("brand", "")
    product = state.get("target_product", "")
    audience = state.get("target_audience", "")
    selling_points = state.get("key_selling_points", "")
    search_trends = state.get("target_search_trends", {})
    yt_trends = state.get("target_yt_trends", {})
    yt_analysis = state.get("yt_video_analysis", "")
    prior_insights = state.get("prior_campaign_insights", "No prior insights available")

    # Recall prior insights from Memory Bank
    if not prior_insights or prior_insights == "No prior insights available":
        try:
            import vertexai
            agent_engine_id = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
            if agent_engine_id and brand and product:
                project = os.environ.get("GOOGLE_CLOUD_PROJECT")
                project_number = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER")
                client = vertexai.Client(project=project, location="us-central1")
                resource_name = f"projects/{project_number}/locations/us-central1/reasoningEngines/{agent_engine_id}"
                query = f"{brand} {product} marketing campaign insights"
                results = list(client.agent_engines.memories.retrieve(
                    name=resource_name,
                    scope={"user_id": "default", "memory_type": "campaign_insight"},
                    similarity_search_params={
                        "search_query": query,
                        "top_k": 5,
                    },
                ))
                if results:
                    insights = [
                        getattr(getattr(m, 'memory', m), 'fact', str(m))
                        for m in results
                    ]
                    prior = "\n".join(f"- {i}" for i in insights if i)
                    if prior:
                        prior_insights = prior
                        tool_context.state["prior_campaign_insights"] = prior
        except Exception as e:
            logger.warning(f"[run_research] Memory Bank recall failed: {e}")

    prompt = f"""You are a senior marketing research analyst. Write a comprehensive research report for this campaign.

## Campaign Context
- Brand: {brand}
- Product: {product}
- Target Audience: {audience}
- Key Selling Points: {selling_points}
- Google Search Trends: {search_trends}
- YouTube Trends: {yt_trends}

## YouTube Video Analysis
{yt_analysis}

## Prior Campaign Insights
{prior_insights}

## Write a comprehensive report with these sections:

### Campaign Guide
- Product overview, brand positioning, target audience profile
- Key selling points and competitive advantages

### Search Trend Analysis
- Detailed analysis of each Google Search trend and its relevance
- Opportunities for trend-jacking in campaign messaging

### YouTube Trend Analysis
- Detailed analysis of each YouTube trend and its relevance
- Content format insights

### Key Insights
- Synthesized findings across all data
- Consumer sentiment and behavioral patterns
- Cultural context and timing considerations

### Strategic Recommendations
- 3-5 actionable campaign strategy recommendations
- Messaging themes that bridge trends and product benefits
- Channel and format recommendations

Write the complete report now. Be specific and reference the actual trend titles by name."""

    # Check GCS cache (recovery from previous wave where state was lost)
    gcs_folder = state.get("gcs_folder", "")
    cached_report = _gcs_state_read("combined_final_cited_report", gcs_folder)
    if cached_report and isinstance(cached_report, str) and len(cached_report) >= 500:
        tool_context.state["combined_final_cited_report"] = cached_report
        tool_context.state["_research_pipeline_complete"] = True
        logger.info(f"[run_research] Recovered from GCS cache ({len(cached_report)} chars)")
        return {"status": "ok", "report_length": len(cached_report), "report": cached_report, "source": "gcs_cache"}

    try:
        client = genai.Client(vertexai=True)
        response = client.models.generate_content(
            model=config.critic_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=4096),
                temperature=0.7,
            ),
        )
        report = response.text or ""
        if len(report) >= 500:
            # Write to GCS FIRST (survives AE wave timeouts)
            _gcs_state_write("combined_final_cited_report", report, gcs_folder)
            tool_context.state["combined_final_cited_report"] = report
            tool_context.state["_research_pipeline_complete"] = True
            return {"status": "ok", "report_length": len(report), "report": report}
        else:
            return {"status": "error", "error": f"Report too short ({len(report)} chars)", "report": report}
    except Exception as e:
        logger.error(f"[run_research] Failed: {e}")
        return {"status": "error", "error": str(e)[:200]}


# ===================================================================
# TOOL 3: run_ad_creative
# ===================================================================
def run_ad_creative(tool_context: ToolContext) -> dict:
    """Generate ad copy concepts and visual concepts for the campaign.

    Call this AFTER run_research. Uses a direct Gemini model call to draft,
    critique, and select the best ad copies and visual concepts.

    Returns a dict with the selected ad copies and visual concepts.
    """
    import json as _json

    state = tool_context.state

    # Skip if already complete
    existing_ads = state.get("final_select_ad_copies", {})
    if isinstance(existing_ads, dict):
        existing_ads = existing_ads.get("final_select_ad_copies", [])
    if existing_ads and len(existing_ads) >= 2:
        return {"status": "already_complete", "ad_copies": len(existing_ads)}

    # Check GCS cache (recovery from previous wave where state was lost)
    gcs_folder = state.get("gcs_folder", "")
    cached_ads = _gcs_state_read("final_select_ad_copies", gcs_folder)
    cached_vis = _gcs_state_read("final_select_visual_concepts", gcs_folder)
    if cached_ads and isinstance(cached_ads, dict) and cached_ads.get("final_select_ad_copies"):
        tool_context.state["final_select_ad_copies"] = cached_ads
        if cached_vis:
            tool_context.state["final_select_visual_concepts"] = cached_vis
            tool_context.state["final_select_vis_concepts"] = _gcs_state_read("final_select_vis_concepts", gcs_folder) or cached_vis
        tool_context.state["_ad_creative_complete"] = True
        logger.info("[run_ad_creative] Recovered from GCS cache")
        return {"status": "ok", "ad_copies": cached_ads.get("final_select_ad_copies", []),
                "visual_concepts": (cached_vis or {}).get("final_select_visual_concepts", []),
                "source": "gcs_cache"}

    brand = state.get("brand", "")
    product = state.get("target_product", "")
    audience = state.get("target_audience", "")
    selling_points = state.get("key_selling_points", "")
    search_trends = state.get("target_search_trends", {})
    yt_trends = state.get("target_yt_trends", {})
    research_report = state.get("combined_final_cited_report", "")

    prompt = f"""You are an elite creative director at a top advertising agency.

## Campaign Context
- Brand: {brand}
- Product: {product}
- Target Audience: {audience}
- Key Selling Points: {selling_points}
- Google Search Trends: {search_trends}
- YouTube Trends: {yt_trends}

## Research Report
{research_report[:5000]}

## Your Task

Complete ALL phases below in a SINGLE response:

### Phase 1: Draft 10 Ad Copies
For each, provide: name, headline, body_text, call_to_action, caption, trend_ref, rationale.
Every concept MUST reference ACTUAL trend titles from the trends data.

### Phase 2: Critique & Select Top 2
Score each on: Trend Alignment, Audience Appeal, Selling Point Integration, Platform Suitability, Memorability (all 1-10).
Select the TOP 2.

### Phase 3: Draft Visual Concepts
For each of the 2 selected ad copies, generate 2 visual concepts.
Each needs: name, type, trend_ref, headline, call_to_action, caption, creative_explain, rationale, prompt (200+ word Imagen/Veo prompt).

### Phase 4: Select Top 2 Visual Concepts
One per ad copy. The strongest visual for each.

### Phase 5: Output JSON
At the END of your response, output TWO JSON blocks:

```json_ad_copies
[{{"name": "...", "headline": "...", "body_text": "...", "call_to_action": "...", "caption": "...", "trend_ref": "...", "rationale": "..."}}]
```

```json_visual_concepts
[{{"name": "...", "type": "...", "trend_ref": "...", "headline": "...", "call_to_action": "...", "caption": "...", "creative_explain": "...", "rationale": "...", "prompt": "..."}}]
```

Be bold and creative. Ground every decision in the research findings."""

    try:
        client = genai.Client(vertexai=True)
        response = client.models.generate_content(
            model=config.worker_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=4096),
                temperature=1.2,
            ),
        )
        creative_text = response.text or ""

        # Parse JSON blocks from the response
        ad_copies = []
        visual_concepts = []

        # Try to extract json_ad_copies block
        ad_match = re.search(r'```json_ad_copies\s*\n(.*?)\n```', creative_text, re.DOTALL)
        if ad_match:
            try:
                ad_copies = _json.loads(ad_match.group(1))
            except _json.JSONDecodeError:
                pass

        # Try to extract json_visual_concepts block
        vis_match = re.search(r'```json_visual_concepts\s*\n(.*?)\n```', creative_text, re.DOTALL)
        if vis_match:
            try:
                visual_concepts = _json.loads(vis_match.group(1))
            except _json.JSONDecodeError:
                pass

        # Fallback: try generic JSON blocks
        if not ad_copies or not visual_concepts:
            json_blocks = re.findall(r'```(?:json)?\s*\n(\[.*?\])\n```', creative_text, re.DOTALL)
            for block in json_blocks:
                try:
                    parsed = _json.loads(block)
                    if isinstance(parsed, list) and parsed:
                        if "headline" in parsed[0] and "body_text" in parsed[0] and not ad_copies:
                            ad_copies = parsed
                        elif "prompt" in parsed[0] and not visual_concepts:
                            visual_concepts = parsed
                except _json.JSONDecodeError:
                    continue

        # Persist to state + GCS write-through
        gcs_folder = state.get("gcs_folder", "")
        if ad_copies:
            ad_data = {"final_select_ad_copies": ad_copies[:2]}
            tool_context.state["final_select_ad_copies"] = ad_data
            _gcs_state_write("final_select_ad_copies", ad_data, gcs_folder)
        if visual_concepts:
            vis_data = {"final_select_visual_concepts": visual_concepts[:2]}
            tool_context.state["final_select_visual_concepts"] = vis_data
            tool_context.state["final_select_vis_concepts"] = {"final_select_vis_concepts": visual_concepts[:2]}
            _gcs_state_write("final_select_visual_concepts", vis_data, gcs_folder)
            _gcs_state_write("final_select_vis_concepts", {"final_select_vis_concepts": visual_concepts[:2]}, gcs_folder)

        tool_context.state["_ad_creative_complete"] = True
        tool_context.state["ad_creative_output"] = creative_text
        _gcs_state_write("ad_creative_output", creative_text, gcs_folder)

        return {
            "status": "ok",
            "ad_copies_count": len(ad_copies),
            "visual_concepts_count": len(visual_concepts),
            "ad_copies": ad_copies[:2],
            "visual_concepts": visual_concepts[:2],
            "creative_text": creative_text,
        }
    except Exception as e:
        logger.error(f"[run_ad_creative] Failed: {e}")
        return {"status": "error", "error": str(e)[:200]}


# ===================================================================
# TOOL 4: generate_images
# ===================================================================
async def generate_images(tool_context: ToolContext) -> dict:
    """Generate 3 reference images (product, person, trend) using Imagen 4 with Gecko quality scoring.

    Call this AFTER run_ad_creative. Generates images in parallel, uploads to GCS,
    and scores each with Gecko fidelity. Images below 0.7 score will be flagged.

    Returns a dict with image generation results and Gecko scores.
    """
    state = tool_context.state
    product = state.get("target_product", "the product")
    audience = state.get("target_audience", "consumers")
    brand = state.get("brand", "")
    ksp = state.get("key_selling_points", "")
    gcs_folder = state.get("gcs_folder", "")
    bucket = os.getenv("BUCKET", "")

    # Get ad creative context
    ad_copies = state.get("final_select_ad_copies", {})
    if isinstance(ad_copies, dict):
        ad_copies = ad_copies.get("final_select_ad_copies", [])
    idea_name = "campaign"
    ad_headline = ""
    if ad_copies and isinstance(ad_copies[0], dict):
        idea_name = ad_copies[0].get("name", "campaign").replace(",", "").replace(" ", "_")
        ad_headline = ad_copies[0].get("headline", "")

    visual_concepts = state.get("final_select_visual_concepts") or state.get("final_select_vis_concepts") or {}
    if isinstance(visual_concepts, dict):
        visual_concepts = visual_concepts.get("final_select_visual_concepts") or visual_concepts.get("final_select_vis_concepts") or []
    visual_prompt_hint = ""
    if visual_concepts and isinstance(visual_concepts[0], dict):
        visual_prompt_hint = visual_concepts[0].get("prompt", "")

    trend_context = _get_trend_context({k: state.get(k) for k in ["target_search_trends", "target_yt_trends", "img_artifact_keys"]})

    # Build 3 shot definitions
    shot_list = [
        {
            "concept_name": f"{idea_name}_product_asset",
            "shot_type": "product_asset",
            "reference_type": "ASSET",
            "prompt": (
                f"Studio product photo: {brand} {product} bottle prominently displayed"
                + (f", {ksp}" if ksp else "")
                + ". Clean white background, dramatic studio lighting, premium beauty product aesthetic. "
                f"No text, no watermarks, no logos."
            ),
        },
        {
            "concept_name": f"{idea_name}_person_asset",
            "shot_type": "person_asset",
            "reference_type": "ASSET",
            "prompt": (
                f"Lifestyle photo: {audience} person"
                + (f' embodying "{ad_headline}"' if ad_headline else "")
                + f", interacting with {product}"
                + (f", {trend_context}" if trend_context else "")
                + ". Warm natural light, modern setting, authentic emotion. "
                f"No text, no watermarks."
            ),
        },
        {
            "concept_name": f"{idea_name}_trend_asset",
            "shot_type": "trend_asset",
            "reference_type": "ASSET",
            "prompt": (
                f"Cinematic lifestyle scene: {brand} {product}"
                + (f" placed in a setting that evokes {trend_context}" if trend_context else "")
                + (f". Visual direction: {visual_prompt_hint[:250]}" if visual_prompt_hint else "")
                + f". The product is clearly visible in the scene"
                + f", {audience} aesthetic, aspirational and culturally resonant"
                + ". Cinematic color grading, golden-hour lighting. "
                f"No text, no watermarks, no logos."
            ),
        },
    ]

    # Check existing images
    existing_imgs = state.get("img_artifact_keys", {})
    if isinstance(existing_imgs, dict):
        existing_imgs = existing_imgs.get("img_artifact_keys", [])
    if not isinstance(existing_imgs, list):
        existing_imgs = []

    img_slots = list(existing_imgs)
    while len(img_slots) < MAX_IMAGES:
        img_slots.append(None)

    slots_to_generate = []
    for i, shot in enumerate(shot_list):
        fail_count = state.get(f"_img_fail_{i}", 0)
        existing = img_slots[i]
        if fail_count >= MAX_IMG_RETRIES:
            if not existing or not existing.get("skipped"):
                safe = re.sub(r"[^a-zA-Z0-9_\-]", "", shot["concept_name"].replace(" ", "_"))
                img_slots[i] = {"artifact_key": f"skipped_{safe}_0.png", "concept_name": shot["concept_name"], "shot_type": shot["shot_type"], "reference_type": "ASSET", "skipped": True}
            continue
        if existing is None:
            slots_to_generate.append((i, shot, fail_count))
        elif existing.get("skipped"):
            continue
        elif existing.get("fidelity_score") is not None and existing["fidelity_score"] < GECKO_THRESHOLD:
            failing_verdicts = existing.get("gecko_failing_verdicts", [])
            if failing_verdicts:
                shot = dict(shot)
                shot["prompt"] = shot["prompt"].rstrip(". ") + f". IMPORTANT: Fix these quality issues: [{'; '.join(failing_verdicts[:5])}]."
            slots_to_generate.append((i, shot, fail_count))

    if not slots_to_generate:
        return {"status": "ok", "message": "All images already generated and verified", "images": [m for m in img_slots if m]}

    # Pre-increment failure counters
    for i, _, fc in slots_to_generate:
        tool_context.state[f"_img_fail_{i}"] = fc + 1

    # Parallel image generation
    img_client = _get_media_client()
    gecko_prompt = state.get("key_selling_points", product)
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

    def _gen_upload_score(idx: int, shot_def: dict) -> dict:
        concept_name = shot_def["concept_name"]
        prompt = shot_def["prompt"]
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "", concept_name.replace(" ", "_"))
        artifact_key = f"{safe_name}_0.png"

        t0 = time.time()
        response = img_client.models.generate_images(
            model="imagen-4.0-generate-preview-06-06",
            prompt=prompt,
            config=GenerateImagesConfig(number_of_images=1),
        )
        gen_elapsed = time.time() - t0

        if not response or not response.generated_images:
            return {"idx": idx, "error": "empty_response"}

        gen_img = response.generated_images[0]
        image_bytes = gen_img.image.image_bytes if gen_img.image else None
        if not image_bytes:
            return {"idx": idx, "error": "no_image_bytes"}

        # Upload to GCS
        gcs_uri = ""
        if bucket and gcs_folder:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            try:
                upload_blob_to_gcs(source_file_name=tmp_path, destination_blob_name=os.path.join(gcs_folder, artifact_key))
                gcs_uri = f"{bucket}/{gcs_folder}/{artifact_key}"
            finally:
                os.unlink(tmp_path)

        img_meta = {
            "artifact_key": artifact_key,
            "img_prompt": prompt[:500],
            "concept": concept_name,
            "concept_name": concept_name,
            "shot_type": shot_def["shot_type"],
            "reference_type": shot_def.get("reference_type", "ASSET"),
            "auto_saved": True,
        }
        if gcs_uri:
            img_meta["gcs_uri"] = gcs_uri

        # Gecko fidelity scoring
        if gcs_uri and gen_elapsed < 30:
            try:
                result = gecko_evaluate(prompt=gecko_prompt, media_uri=gcs_uri, media_type="image", project_id=project_id, location="us-central1")
                if isinstance(result, dict) and result.get("status") == "success":
                    img_meta["fidelity_score"] = result.get("score", 0.0)
                    if result.get("failing"):
                        img_meta["gecko_failing_verdicts"] = result["failing"]
                    if result.get("passing"):
                        img_meta["gecko_passing_verdicts"] = result["passing"]
                elif isinstance(result, (int, float)):
                    img_meta["fidelity_score"] = float(result)
            except Exception as e:
                logger.warning(f"[generate_images] Gecko eval failed for {concept_name}: {e}")

        return {"idx": idx, "img_meta": img_meta, "image_bytes": image_bytes, "artifact_key": artifact_key, "gen_elapsed": gen_elapsed}

    results_map = {}
    with ThreadPoolExecutor(max_workers=len(slots_to_generate)) as pool:
        futures = {pool.submit(_gen_upload_score, i, shot): (i, shot, fc) for i, shot, fc in slots_to_generate}
        for fut in as_completed(futures):
            i, shot, fc = futures[fut]
            try:
                results_map[i] = fut.result()
            except Exception as e:
                results_map[i] = {"idx": i, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    # Process results
    image_results = []
    for i, shot, fc in slots_to_generate:
        result = results_map.get(i, {"idx": i, "error": "no_result"})
        if "error" in result:
            image_results.append({"slot": i, "shot_type": shot["shot_type"], "error": result["error"], "retry": f"{fc+1}/{MAX_IMG_RETRIES}"})
            continue

        img_meta = result["img_meta"]
        score = img_meta.get("fidelity_score")
        img_slots[i] = img_meta

        gecko_passed = score is None or score >= GECKO_THRESHOLD
        if gecko_passed:
            tool_context.state[f"_img_fail_{i}"] = 0

        # Save as ADK artifact so ADK web UI shows inline
        image_bytes = result.get("image_bytes")
        if image_bytes:
            try:
                art_part = types.Part(inline_data=types.Blob(mime_type="image/png", data=image_bytes))
                await tool_context.save_artifact(filename=img_meta["artifact_key"], artifact=art_part)
            except Exception as e:
                logger.warning(f"[generate_images] save_artifact failed: {e}")

        image_results.append({
            "slot": i,
            "shot_type": shot["shot_type"],
            "concept_name": img_meta["concept_name"],
            "gecko_score": f"{score:.2f}" if score is not None else "skipped",
            "gecko_passed": gecko_passed,
            "gcs_uri": img_meta.get("gcs_uri", ""),
        })

    # Persist image list
    current_list = [m for m in img_slots if m is not None]
    tool_context.state["img_artifact_keys"] = {"img_artifact_keys": current_list}

    return {"status": "ok", "images_generated": len([r for r in image_results if "error" not in r]), "image_results": image_results}


# ===================================================================
# TOOL 5: generate_commercial
# ===================================================================
def generate_commercial(tool_context: ToolContext) -> dict:
    """Generate a commercial video using Veo 3.1 with ASSET reference images from the campaign.

    Call this AFTER generate_images. Submits a Veo video generation job and polls
    for completion within the AE wave budget. If not done, saves the operation
    for resumption on the next wave.

    Returns a dict with the commercial video URI and metadata.
    """
    state = tool_context.state
    product = state.get("target_product", "the product")
    audience = state.get("target_audience", "target consumers")
    selling_points = state.get("key_selling_points", "")
    duration = state.get("commercial_duration", 8)
    brand = state.get("brand", "")
    gcs_folder = state.get("gcs_folder", "")
    bucket = os.getenv("BUCKET", "")
    bucket_name = bucket.replace("gs://", "")

    # Check GCS cache (recovery from previous wave where state was lost)
    gcs_folder = state.get("gcs_folder", "")
    cached_commercial = _gcs_state_read("commercial_artifact", gcs_folder)
    if cached_commercial and isinstance(cached_commercial, dict) and cached_commercial.get("gcs_uri"):
        tool_context.state["commercial_artifact"] = cached_commercial
        tool_context.state["vid_artifact_keys"] = {"vid_artifact_keys": [cached_commercial]}
        logger.info(f"[generate_commercial] Recovered from GCS cache: {cached_commercial.get('gcs_uri', '')[:80]}")
        return {"status": "ok", "gcs_uri": cached_commercial["gcs_uri"], "commercial": cached_commercial, "source": "gcs_cache"}

    veo_client = _get_media_client()
    clips_cache = state.get("_commercial_clips", {})
    pending_op = clips_cache.get("_pending_veo_op") if isinstance(clips_cache, dict) else None

    # Track runs
    av_runs = state.get("_av_studio_runs", 0) + 1
    tool_context.state["_av_studio_runs"] = av_runs
    if av_runs > AV_STUDIO_MAX_RUNS * 3:
        return {"status": "skipped", "reason": f"Max AV studio runs exceeded ({av_runs})"}

    # Build reference images
    reference_images = _build_veo_reference_images({k: state.get(k) for k in ["target_search_trends", "target_yt_trends", "img_artifact_keys"]}, bucket, gcs_folder)

    # Get creative context
    trend_context = _get_trend_context({k: state.get(k) for k in ["target_search_trends", "target_yt_trends", "img_artifact_keys"]})
    ad_copies = state.get("final_select_ad_copies", {})
    if isinstance(ad_copies, dict):
        ad_copies = ad_copies.get("final_select_ad_copies", [])
    ad_headline = ""
    if ad_copies and isinstance(ad_copies[0], dict):
        ad_headline = ad_copies[0].get("headline", "")

    visual_concepts = state.get("final_select_visual_concepts") or state.get("final_select_vis_concepts") or {}
    if isinstance(visual_concepts, dict):
        visual_concepts = visual_concepts.get("final_select_visual_concepts") or visual_concepts.get("final_select_vis_concepts") or []
    visual_prompt_hint = ""
    if visual_concepts and isinstance(visual_concepts[0], dict):
        visual_prompt_hint = visual_concepts[0].get("prompt", "")

    clip_prompt = _build_commercial_prompt(product, audience, selling_points, duration, brand, trend_context, ad_headline, visual_prompt_hint)

    gen_config = GenerateVideosConfig(
        aspect_ratio="16:9", number_of_videos=1, output_gcs_uri=bucket,
        reference_images=reference_images if reference_images else None,
    )

    try:
        if pending_op:
            from google.genai.types import GenerateVideosOperation
            try:
                stub_op = GenerateVideosOperation(name=pending_op)
                operation = veo_client.operations.get(operation=stub_op)
            except Exception as e:
                logger.warning(f"[generate_commercial] Resume failed: {e}")
                pending_op = None

        if not pending_op:
            operation = veo_client.models.generate_videos(model=config.video_gen_model, prompt=clip_prompt, config=gen_config)
            if operation.name:
                tool_context.state["_commercial_clips"] = {"_pending_veo_op": operation.name}
                _gcs_state_write("_pending_veo_op", operation.name, gcs_folder)

        # Poll within wave budget
        start_time = time.time()
        while not operation.done:
            elapsed = time.time() - start_time
            if elapsed > AE_WAVE_POLL_BUDGET:
                tool_context.state["_commercial_clips"] = {"_pending_veo_op": operation.name}
                return {"status": "pending", "message": f"Veo still generating after {int(elapsed)}s - will resume next wave", "operation": operation.name}
            time.sleep(10)
            operation = veo_client.operations.get(operation)

        if operation.error:
            err_msg = str(operation.error)[:200]
            # Retry without reference images
            retry_config = GenerateVideosConfig(aspect_ratio="16:9", number_of_videos=1, output_gcs_uri=bucket)
            operation = veo_client.models.generate_videos(model=config.video_gen_model, prompt=clip_prompt, config=retry_config)
            if operation.name:
                tool_context.state["_commercial_clips"] = {"_pending_veo_op": operation.name}
            return {"status": "retrying", "message": f"Veo failed ({err_msg}), retrying without references", "operation": operation.name if operation.name else ""}

        # Extract video URI
        video_uri = None
        if operation.result and operation.result.generated_videos:
            for video in operation.result.generated_videos:
                if video.video and video.video.uri:
                    video_uri = video.video.uri
                    break

        if not video_uri:
            tool_context.state["_commercial_clips"] = {"_pending_veo_op": ""}
            return {"status": "error", "error": "No video URI in result"}

        final_gcs_uri = video_uri

        # Copy to canonical name
        try:
            source_blob = video_uri.replace(f"gs://{bucket_name}/", "")
            video_bytes = download_blob(bucket_name=bucket_name, source_blob_name=source_blob)
            if gcs_folder and bucket:
                art_blob = f"{gcs_folder}/commercial_{duration}s.mp4"
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                    tmp.write(video_bytes)
                    tmp_path = tmp.name
                try:
                    upload_blob_to_gcs(source_file_name=tmp_path, destination_blob_name=art_blob)
                    final_gcs_uri = f"{bucket}/{art_blob}"
                finally:
                    os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"[generate_commercial] Video copy failed: {e}")

        commercial_data = {
            "artifact_key": f"commercial_{duration}s.mp4",
            "gcs_uri": final_gcs_uri,
            "metadata": {
                "title": f"{duration}s commercial for {product}",
                "scene_descriptions": [clip_prompt[:200]],
                "total_clips": 1,
                "duration_seconds": duration,
                "narrative_arc": f"Trend-driven commercial for {brand} {product}",
                "target_audience_appeal": f"Designed for {audience}",
                "trend_connections": trend_context or "N/A",
                "has_audio": True,
                "deterministic_av_studio": True,
            },
        }
        # GCS write-through FIRST
        _gcs_state_write("commercial_artifact", commercial_data, gcs_folder)
        tool_context.state["commercial_artifact"] = commercial_data
        tool_context.state["vid_artifact_keys"] = {"vid_artifact_keys": [commercial_data]}
        tool_context.state["_commercial_clips"] = {}
        return {"status": "ok", "gcs_uri": final_gcs_uri, "duration": duration, "commercial": commercial_data}

    except Exception as e:
        logger.warning(f"[generate_commercial] Exception: {e}")
        return {"status": "error", "error": str(e)[:200]}


# ===================================================================
# TOOL 6: run_focus_group
# ===================================================================
def run_focus_group(tool_context: ToolContext) -> dict:
    """Run a full focus group with portraits, Chirp voiceovers, Ken Burns video, Lyria music, and evaluation.

    Call this AFTER generate_commercial. Produces:
    1. 3 panelist portraits (Imagen 4)
    2. 3 Chirp HD voiceover testimonials
    3. 3 Ken Burns zoom videos (portrait + voiceover)
    4. Lyria 2 background music
    5. Concatenated focus group reel
    6. Text evaluation with scores and Go/No-Go

    Returns a dict with the evaluation text, scores, and video assets.
    """
    import json as _json
    import subprocess

    state = tool_context.state
    brand = state.get("brand", "")
    product = state.get("target_product", "")
    audience = state.get("target_audience", "")
    selling_points = state.get("key_selling_points", "")
    research_report = state.get("combined_final_cited_report", "")[:2000]
    ad_copies = state.get("final_select_ad_copies", {})
    if isinstance(ad_copies, dict):
        ad_copies = ad_copies.get("final_select_ad_copies", [])
    visual_concepts = state.get("final_select_visual_concepts") or state.get("final_select_vis_concepts") or {}
    if isinstance(visual_concepts, dict):
        visual_concepts = visual_concepts.get("final_select_visual_concepts") or visual_concepts.get("final_select_vis_concepts") or []
    commercial = state.get("commercial_artifact", {})
    img_keys = state.get("img_artifact_keys", {})
    if isinstance(img_keys, dict):
        img_keys = img_keys.get("img_artifact_keys", [])
    trend_context = _get_trend_context({k: state.get(k) for k in ["target_search_trends", "target_yt_trends", "img_artifact_keys"]})
    gcs_folder = state.get("gcs_folder", "")
    bucket = os.getenv("BUCKET", "gs://zghost-media-center")

    # Skip if already complete
    existing_eval = state.get("focus_group_evaluation", "")
    if existing_eval and len(existing_eval) > 200:
        return {"status": "already_complete", "evaluation_length": len(existing_eval),
                "evaluation": existing_eval[:500] + "..."}

    # Check GCS cache (recovery from previous wave where state was lost)
    gcs_folder = state.get("gcs_folder", "")
    cached_eval = _gcs_state_read("focus_group_evaluation", gcs_folder)
    if cached_eval and isinstance(cached_eval, str) and len(cached_eval) > 200:
        tool_context.state["focus_group_evaluation"] = cached_eval
        tool_context.state["_focus_group_complete"] = True
        logger.info(f"[run_focus_group] Recovered from GCS cache ({len(cached_eval)} chars)")
        return {"status": "ok", "evaluation_length": len(cached_eval),
                "evaluation": cached_eval, "source": "gcs_cache"}

    # Track attempts
    fg_count = state.get("_focus_group_attempts", 0) + 1
    tool_context.state["_focus_group_attempts"] = fg_count
    if fg_count > 5:
        tool_context.state["_focus_group_complete"] = True
        return {"status": "skipped", "reason": "Max focus group attempts exceeded"}

    # Step 1: Generate focus group evaluation text (with panelist personas + testimonials)
    eval_prompt = f"""You are simulating a FOCUS GROUP evaluation of a marketing campaign.

## Campaign
- Brand: {brand}
- Product: {product}
- Target Audience: {audience}
- Key Selling Points: {selling_points}

## Research Summary
{research_report}

## Creative Assets
- Ad Copies: {ad_copies}
- Visual Concepts: {visual_concepts}
- Commercial: {commercial}
- Reference Images: {len(img_keys) if isinstance(img_keys, list) else 0} generated
- Trend Connection: {trend_context}

## Instructions

Simulate a 3-person focus group with diverse perspectives from the target audience ({audience}).

For each panelist, provide ALL of these fields:
1. **name**: A realistic full name
2. **age**: An age appropriate for the target audience
3. **occupation**: Their job/role
4. **persona**: A brief description of their personality, interests, and lifestyle (used for portrait generation)
5. **voice_style**: One of: "young_female", "young_male", "mature_female", "mature_male", "british_female"
6. **testimonial**: A 2-3 sentence spoken testimonial quote (what they'd say on camera)
7. **scores**: Rate on 5 dimensions (1-10 each): creative_impact, brand_alignment, trend_relevance, purchase_intent, emotional_response

## Output Format
Output a JSON block with the panelists AND the overall assessment:

```json_focus_group
{{
  "panelists": [
    {{
      "name": "...",
      "age": 25,
      "occupation": "...",
      "persona": "...",
      "voice_style": "young_female",
      "testimonial": "...",
      "scores": {{"creative_impact": 8, "brand_alignment": 7, "trend_relevance": 9, "purchase_intent": 7, "emotional_response": 8}}
    }}
  ],
  "overall_score": 8.0,
  "go_no_go": "GO",
  "improvement_suggestions": ["...", "...", "..."]
}}
```

Then write a narrative evaluation with detailed analysis."""

    evaluation = ""
    panelists_data = []
    overall_score = 0.0
    go_no_go = "PENDING"

    try:
        client = genai.Client(vertexai=True)
        response = client.models.generate_content(
            model=config.critic_model,
            contents=eval_prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=4096),
                temperature=0.7,
            ),
        )
        evaluation = response.text or ""

        # Parse JSON block from evaluation
        fg_match = re.search(r'```json_focus_group\s*\n(.*?)\n```', evaluation, re.DOTALL)
        if not fg_match:
            fg_match = re.search(r'```json\s*\n(\{.*?"panelists".*?\})\n```', evaluation, re.DOTALL)
        if fg_match:
            try:
                fg_data = _json.loads(fg_match.group(1))
                panelists_data = fg_data.get("panelists", [])
                overall_score = fg_data.get("overall_score", 0.0)
                go_no_go = fg_data.get("go_no_go", "PENDING")
            except _json.JSONDecodeError:
                logger.warning("[run_focus_group] Could not parse JSON from evaluation")
    except Exception as e:
        logger.error(f"[run_focus_group] Evaluation failed: {e}")
        return {"status": "error", "error": str(e)[:200]}

    if len(evaluation) < 200:
        return {"status": "error", "error": f"Evaluation too short ({len(evaluation)} chars)"}

    # Save evaluation text FIRST — GCS write-through ensures recovery across AE waves
    gcs_folder = state.get("gcs_folder", "")
    _gcs_state_write("focus_group_evaluation", evaluation, gcs_folder)
    tool_context.state["focus_group_evaluation"] = evaluation
    tool_context.state["_focus_group_complete"] = True

    # Step 2: Generate portraits, voiceovers, Ken Burns videos for each panelist
    # NOTE: On AE, Imagen/Chirp/ffmpeg will timeout. The evaluation text is already saved,
    # so the pipeline can proceed to save_report even if media generation fails.
    from .skills.focus_group.tools import (
        PANELIST_VOICES,
        _generate_lyria_background_music,
    )
    from google.cloud import texttospeech_v1beta1 as texttospeech
    from .shared_libraries.utils import download_blob

    img_client = _get_media_client()
    tts_client = texttospeech.TextToSpeechClient()
    bucket_name = bucket.replace("gs://", "")
    panelist_results = []

    for i, panelist in enumerate(panelists_data[:3]):
        p_name = panelist.get("name", f"Panelist_{i+1}")
        p_age = panelist.get("age", 30)
        p_persona = panelist.get("persona", "consumer")
        p_voice = panelist.get("voice_style", "young_female")
        p_testimonial = panelist.get("testimonial", "This is a great product.")
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "", p_name.replace(" ", "_"))

        p_result = {"name": p_name, "age": p_age, "persona": p_persona}

        # 2a: Generate portrait
        try:
            portrait_prompt = (
                f"Professional headshot photograph of a {p_age}-year-old person matching this "
                f"consumer persona: {p_persona}. "
                f"Natural lighting, friendly genuine smile, neutral soft-focus background. "
                f"High-quality portrait photography. Approachable and authentic."
            )
            from google.genai.types import GenerateImagesConfig
            portrait_resp = img_client.models.generate_images(
                model="imagen-4.0-generate-preview-06-06",
                prompt=portrait_prompt,
                config=GenerateImagesConfig(number_of_images=1),
            )
            if portrait_resp and portrait_resp.generated_images:
                portrait_bytes = portrait_resp.generated_images[0].image.image_bytes
                portrait_key = f"panelist_{safe_name}.png"
                portrait_dir = "session_media/focus_group/portraits"
                os.makedirs(portrait_dir, exist_ok=True)
                portrait_path = os.path.join(portrait_dir, portrait_key)
                with open(portrait_path, "wb") as f:
                    f.write(portrait_bytes)

                # Upload to GCS
                if gcs_folder:
                    dest = f"{gcs_folder}/focus_group/{portrait_key}"
                    upload_blob_to_gcs(source_file_name=portrait_path, destination_blob_name=dest)
                    p_result["portrait_gcs_uri"] = f"{bucket}/{dest}"
                p_result["portrait_local"] = portrait_path
                p_result["portrait_artifact"] = portrait_key
                logger.info(f"[focus_group] Portrait generated: {p_name}")
            else:
                logger.warning(f"[focus_group] Portrait empty for {p_name}")
        except Exception as e:
            logger.warning(f"[focus_group] Portrait failed for {p_name}: {e}")

        # 2b: Generate Chirp voiceover
        try:
            voice_config = PANELIST_VOICES.get(p_voice, PANELIST_VOICES["young_female"])
            ssml = f'<speak><prosody rate="1.0">{p_testimonial}</prosody></speak>'
            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_config["language_code"],
                name=voice_config["name"],
            )
            audio_cfg = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                sample_rate_hertz=48000,
            )
            tts_resp = tts_client.synthesize_speech(
                request=texttospeech.SynthesizeSpeechRequest(
                    input=texttospeech.SynthesisInput(ssml=ssml),
                    voice=voice, audio_config=audio_cfg,
                )
            )
            vo_dir = "session_media/focus_group/voiceover"
            os.makedirs(vo_dir, exist_ok=True)
            vo_path = os.path.join(vo_dir, f"panelist_vo_{safe_name}.mp3")
            with open(vo_path, "wb") as f:
                f.write(tts_resp.audio_content)
            if gcs_folder:
                dest = f"{gcs_folder}/focus_group/voiceover/panelist_vo_{safe_name}.mp3"
                upload_blob_to_gcs(source_file_name=vo_path, destination_blob_name=dest)
                p_result["voiceover_gcs_uri"] = f"{bucket}/{dest}"
            p_result["voiceover_local"] = vo_path
            logger.info(f"[focus_group] Voiceover generated: {p_name} ({voice_config['name']})")
        except Exception as e:
            logger.warning(f"[focus_group] Voiceover failed for {p_name}: {e}")

        # 2c: Ken Burns video (portrait + voiceover)
        portrait_local = p_result.get("portrait_local")
        vo_local = p_result.get("voiceover_local")
        if portrait_local and vo_local and os.path.exists(portrait_local) and os.path.exists(vo_local):
            try:
                # Probe audio duration
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", vo_local],
                    capture_output=True, text=True, timeout=10,
                )
                try:
                    audio_dur = float(probe.stdout.strip())
                except (ValueError, AttributeError):
                    audio_dur = 15.0
                video_dur = audio_dur + 0.5

                vid_dir = "session_media/focus_group/testimonials"
                os.makedirs(vid_dir, exist_ok=True)
                vid_key = f"panelist_testimonial_{safe_name}.mp4"
                vid_path = os.path.join(vid_dir, vid_key)
                fps = 30
                total_frames = int(video_dur * fps)

                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1", "-i", portrait_local,
                    "-i", vo_local,
                    "-filter_complex",
                    (
                        "[0:v]"
                        "scale=2160:2160:force_original_aspect_ratio=decrease,"
                        "pad=2160:2160:(ow-iw)/2:(oh-ih)/2:black,"
                        f"zoompan=z='1+0.15*on/{total_frames}':"
                        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={total_frames}:s=1920x1080:fps={fps}"
                        "[v]"
                    ),
                    "-map", "[v]", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    "-t", f"{video_dur:.2f}",
                    "-pix_fmt", "yuv420p",
                    vid_path,
                ]
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    if gcs_folder:
                        dest = f"{gcs_folder}/focus_group/{vid_key}"
                        upload_blob_to_gcs(source_file_name=vid_path, destination_blob_name=dest)
                        p_result["testimonial_video_gcs_uri"] = f"{bucket}/{dest}"
                    p_result["testimonial_video_local"] = vid_path
                    p_result["testimonial_video_artifact"] = vid_key
                    logger.info(f"[focus_group] Ken Burns video: {p_name} ({video_dur:.1f}s)")
                else:
                    logger.warning(f"[focus_group] ffmpeg failed for {p_name}: {result.stderr[:200]}")
            except Exception as e:
                logger.warning(f"[focus_group] Ken Burns failed for {p_name}: {e}")

        panelist_results.append(p_result)

    # Step 3: Generate Lyria background music
    lyria_path = None
    try:
        music_bytes = _generate_lyria_background_music(brand, product, audience)
        if music_bytes:
            lyria_dir = "session_media/focus_group"
            os.makedirs(lyria_dir, exist_ok=True)
            lyria_path = os.path.join(lyria_dir, "background_music.mp3")
            with open(lyria_path, "wb") as f:
                f.write(music_bytes)
            if gcs_folder:
                dest = f"{gcs_folder}/focus_group/background_music.mp3"
                upload_blob_to_gcs(source_file_name=lyria_path, destination_blob_name=dest)
            logger.info("[focus_group] Lyria background music generated")
    except Exception as e:
        logger.warning(f"[focus_group] Lyria music failed (non-fatal): {e}")

    # Step 4: Concatenate panelist videos into a focus group reel
    reel_gcs_uri = ""
    testimonial_videos = [p.get("testimonial_video_local") for p in panelist_results if p.get("testimonial_video_local")]
    if len(testimonial_videos) >= 2:
        try:
            concat_dir = "session_media/focus_group"
            os.makedirs(concat_dir, exist_ok=True)
            concat_list = os.path.join(concat_dir, "concat_list.txt")
            with open(concat_list, "w") as f:
                for vp in testimonial_videos:
                    f.write(f"file '{os.path.abspath(vp)}'\n")

            reel_path = os.path.join(concat_dir, "focus_group_reel.mp4")
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c", "copy", reel_path,
            ]
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.warning(f"[focus_group] Concat failed: {result.stderr[:200]}")
            else:
                # Mix in Lyria music if available
                if lyria_path and os.path.exists(lyria_path):
                    reel_with_music = os.path.join(concat_dir, "focus_group_reel_music.mp4")
                    mix_cmd = [
                        "ffmpeg", "-y",
                        "-i", reel_path, "-i", lyria_path,
                        "-filter_complex",
                        "[1:a]volume=0.15[bg];[0:a][bg]amix=inputs=2:duration=first[aout]",
                        "-map", "0:v", "-map", "[aout]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                        reel_with_music,
                    ]
                    mix_result = subprocess.run(mix_cmd, capture_output=True, text=True, timeout=60)
                    if mix_result.returncode == 0:
                        reel_path = reel_with_music
                        logger.info("[focus_group] Mixed Lyria music into reel")

                if gcs_folder:
                    dest = f"{gcs_folder}/focus_group/focus_group_reel.mp4"
                    upload_blob_to_gcs(source_file_name=reel_path, destination_blob_name=dest)
                    reel_gcs_uri = f"{bucket}/{dest}"
                    logger.info(f"[focus_group] Final reel: {reel_gcs_uri}")
        except Exception as e:
            logger.warning(f"[focus_group] Reel concat failed: {e}")

    # Persist panelist data and reel URI
    tool_context.state["focus_group_panelists"] = {"panelists": panelist_results}
    if reel_gcs_uri:
        tool_context.state["focus_group_reel_gcs_uri"] = reel_gcs_uri
    tool_context.state["_focus_group_complete"] = True

    return {
        "status": "ok",
        "evaluation_length": len(evaluation),
        "evaluation": evaluation,
        "panelists": len(panelist_results),
        "portraits_generated": sum(1 for p in panelist_results if p.get("portrait_artifact")),
        "testimonial_videos": sum(1 for p in panelist_results if p.get("testimonial_video_artifact")),
        "reel_gcs_uri": reel_gcs_uri,
        "overall_score": overall_score,
        "go_no_go": go_no_go,
    }


# ===================================================================
# TOOL 7: save_report
# ===================================================================
async def save_report(tool_context: ToolContext) -> dict:
    """Compile all campaign assets into a branded PDF report and save to GCS.

    Call this LAST in the pipeline. Compiles research, creative assets, commercial,
    and focus group evaluation into a professional PDF.

    Returns a dict with the PDF artifact key and GCS URI.
    """
    state = tool_context.state
    processed_report = state.get("combined_final_cited_report", "")
    gcs_folder = state.get("gcs_folder", "")

    if not processed_report:
        fallback_parts = []
        ad_output = state.get("ad_creative_output", "")
        fg_eval = state.get("focus_group_evaluation", "")
        if ad_output:
            fallback_parts.append(f"## Ad Creative Output\n\n{ad_output}")
        if fg_eval:
            fallback_parts.append(f"## Focus Group Evaluation\n\n{fg_eval}")
        if fallback_parts:
            processed_report = "\n\n---\n\n".join(fallback_parts)
        else:
            tool_context.state["final_report_with_citations"] = "(No report content available)"
            return {"status": "skipped", "reason": "No pipeline content to save"}

    img_keys = state.get("img_artifact_keys", {})
    if isinstance(img_keys, dict):
        img_artifact_list = img_keys.get("img_artifact_keys", [])
    else:
        img_artifact_list = img_keys if isinstance(img_keys, list) else []

    vid_keys = state.get("vid_artifact_keys", {})
    if isinstance(vid_keys, dict):
        vid_artifact_list = vid_keys.get("vid_artifact_keys", [])
    else:
        vid_artifact_list = vid_keys if isinstance(vid_keys, list) else []

    commercial_artifact = state.get("commercial_artifact", {})
    focus_group_evaluation = state.get("focus_group_evaluation", "")
    focus_group_panelists = state.get("focus_group_panelists", {})

    result = await save_final_report_tool(
        processed_report=processed_report,
        img_artifact_list=img_artifact_list,
        vid_artifact_list=vid_artifact_list,
        commercial_artifact=commercial_artifact,
        focus_group_evaluation=focus_group_evaluation,
        focus_group_panelists=focus_group_panelists,
        gcs_folder=gcs_folder,
        save_artifact_fn=tool_context.save_artifact,
        brand=state.get("brand", ""),
        product=state.get("target_product", ""),
        audience=state.get("target_audience", ""),
        selling_points=state.get("key_selling_points", ""),
        target_search_trends=state.get("target_search_trends", ""),
        target_yt_trends=state.get("target_yt_trends", ""),
    )

    status = result.get("status", "failed")
    artifact_key = result.get("artifact_key", "")
    if status == "ok":
        asset_summary = f"\n\n## Creative Assets\n- Images: {len(img_artifact_list)} generated"
        for img in img_artifact_list:
            if isinstance(img, dict):
                asset_summary += f"\n  - {img.get('concept_name', img.get('artifact_key', '?'))}: Gecko {img.get('fidelity_score', 'N/A')}, type: {img.get('reference_type', 'N/A')}"
        if isinstance(commercial_artifact, dict) and commercial_artifact.get("gcs_uri"):
            asset_summary += f"\n- Commercial: {commercial_artifact['gcs_uri']}"
        if focus_group_evaluation:
            asset_summary += f"\n\n## Focus Group\n{str(focus_group_evaluation)[:500]}"

        tool_context.state["final_report_with_citations"] = processed_report + asset_summary
        gcs_bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
        pdf_gcs_uri = f"{gcs_bucket}/{gcs_folder}/{artifact_key}" if gcs_folder else ""
        tool_context.state["pdf_artifact"] = {"artifact_key": artifact_key, "gcs_uri": pdf_gcs_uri, "version": result.get("version")}
        return {"status": "ok", "artifact_key": artifact_key, "gcs_uri": pdf_gcs_uri}
    else:
        tool_context.state["final_report_with_citations"] = processed_report
        return {"status": "error", "error": result.get("error", "unknown")}


# ===================================================================
# Helper: Build Veo reference images
# ===================================================================
def _build_veo_reference_images(state: dict, bucket: str, gcs_folder: str) -> list:
    img_keys = state.get("img_artifact_keys", {})
    if isinstance(img_keys, dict):
        img_list = img_keys.get("img_artifact_keys", [])
    else:
        img_list = img_keys if isinstance(img_keys, list) else []

    reference_images = []
    if not img_list or not gcs_folder or not bucket:
        return reference_images

    _valid = [m for m in img_list if isinstance(m, dict) and not m.get("skipped")]
    product_refs = [m for m in _valid if m.get("shot_type") == "product_asset"]
    trend_refs = [m for m in _valid if m.get("shot_type") == "trend_asset"]
    person_refs = [m for m in _valid if m.get("shot_type") == "person_asset"]

    selected_refs = product_refs[:1] + trend_refs[:1]
    if not trend_refs and person_refs:
        selected_refs = product_refs[:1] + person_refs[:1]

    for img_meta in selected_refs:
        img_gcs_uri = img_meta.get("gcs_uri", "")
        if not img_gcs_uri:
            img_filename = img_meta.get("artifact_key", "")
            if not img_filename:
                continue
            img_gcs_uri = f"{bucket}/{gcs_folder}/{img_filename}"
        reference_images.append(
            types.VideoGenerationReferenceImage(
                image=types.Image(gcs_uri=img_gcs_uri, mime_type="image/png"),
                reference_type=types.VideoGenerationReferenceType.ASSET,
            )
        )
    return reference_images


# ===================================================================
# Helper: Build commercial prompt
# ===================================================================
def _build_commercial_prompt(
    product: str, audience: str, selling_points: str, duration: int,
    brand: str = "", trend_context: str = "",
    ad_headline: str = "", visual_prompt_hint: str = "",
) -> str:
    trend_line = f"TREND INTEGRATION: Visually evoke {trend_context} through the aesthetic, setting, and mood. " if trend_context else ""
    concept_line = f'CREATIVE CONCEPT: "{ad_headline}" -- ' if ad_headline else ""
    visual_direction = f"VISUAL DIRECTION: {visual_prompt_hint[:300]}. " if visual_prompt_hint else ""
    return (
        f"A cinematic {duration}-second commercial for {brand} {product}. "
        f"{concept_line}"
        f"NARRATIVE: A {audience} discovers {brand} {product} -- moment of genuine delight "
        f"as they experience the product -- product in action showcasing its benefits -- "
        f"close-up hero shot of the {brand} product packaging with branding visible. "
        f"{trend_line}"
        f"{visual_direction}"
        f"VISUAL STYLE: Premium commercial quality, warm golden-hour lighting, "
        f"shallow depth of field, smooth camera movements, cinematic color grading. "
        f"CAMERA: Start medium-wide, dolly in to close-up on product, "
        f"slow push-in to branded hero moment. Smooth transitions. "
        f"MOOD: Fresh, uplifting, naturally luxurious. "
        f"PRODUCT BRANDING: The {brand} name and product label must appear naturally in at least one shot. "
        f"{selling_points[:200]}. "
        f"SUPPRESS SUBTITLES. NO WATERMARKS."
    )


# ===================================================================
# ORCHESTRATOR INSTRUCTION
# ===================================================================
ORCHESTRATOR_INSTRUCTION = """You are a marketing campaign orchestrator AI. You help users build complete marketing campaigns through an interactive, conversational experience.

## Your Personality

You are a seasoned Chief Marketing Officer. You're warm, knowledgeable, and decisive. You explain your reasoning and make the user feel like they're working with a world-class marketing team. Use the brand name and product naturally in conversation.

## Pipeline (8 tools, called in sequence)

1. **gather_trends** - Fetch live Google Search + YouTube trends (parallel, cached 1hr)
2. **select_trend** - Save the user's trend picks (search + YouTube)
3. **run_research** - Generate comprehensive research report
4. **run_ad_creative** - Draft, critique, and select ad copies + visual concepts
5. **generate_images** - Create 3 reference images with Gecko quality scoring
6. **generate_commercial** - Generate video commercial with Veo 3.1
7. **run_focus_group** - Simulate focus group evaluation
8. **save_report** - Compile everything into a branded PDF

## Interactive Flow

### Step 1: Welcome & Campaign Setup
FIRST, check session state for `brand`, `target_product`, `target_audience`, `key_selling_points`.
If ALL are present, greet the user briefly and proceed IMMEDIATELY to Step 2 (call gather_trends).
Only ask for missing details if the state is empty.

### Step 2: Trend Discovery (INTERACTIVE)
Call `gather_trends` to fetch live trends. Then PRESENT BOTH TABLES to the user:

**Google Search Trends:**
Show the full table from the tool result.

**YouTube Trends:**
Show the full table from the tool result.

Ask: "Which Google Search trend number and YouTube trend number would you like to target for this campaign?"

**WAIT for the user to respond with their picks before proceeding.**

### Step 3: Save Selections
Once the user picks trends, call `select_trend(search_trend_number=N, youtube_trend_number=M)`.
Confirm their selections back to them.

### Step 4-8: Pipeline Execution
After trends are selected, run the remaining pipeline stages **ONE TOOL PER RESPONSE**. You MUST follow this pattern for EVERY stage:

1. Call exactly ONE tool
2. STOP and wait for the tool result
3. Write a 2-4 sentence summary of what happened
4. Tell the user what's coming next
5. Then call the NEXT tool in your next response

**CRITICAL: You MUST output text AFTER each tool result BEFORE calling the next tool. NEVER chain multiple tool calls in a single response. Each response should contain AT MOST one function call.**

Order:
1. run_research → **INCLUDE THE FULL RESEARCH REPORT** in your response. The report is the key deliverable — show the complete text, not just a summary. Include all sections: Campaign Guide, Trend Analysis, Key Insights, Strategic Recommendations.
2. run_ad_creative → show the 2 winning ad copy headlines and their trend hooks
3. generate_images → report ALL 3 Gecko fidelity scores (product, person, trend ASSET types)
4. generate_commercial → report video duration, GCS URI, reference images used
5. run_focus_group → share panelist names, overall score, Go/No-Go verdict, video reel link
6. save_report → announce the PDF GCS URI and what it contains

Between stages, give brief CEO-friendly status updates explaining what was just accomplished and what's next.

## Rules

1. **ALWAYS wait for user input after presenting trends.** Never auto-select trends.
2. **Check state before each step**: Skip tools whose output already exists.
3. **Handle errors gracefully**: Note failures and continue to the next stage.
4. **Pending Veo operations**: If generate_commercial returns "pending", tell the user to say "continue" to resume.
5. **Always complete**: The pipeline MUST reach save_report.
6. **Show your work**: After each tool, explain what you found/created.

## State Markers (for skipping completed stages)
- Trends done: `target_search_trends` and `target_yt_trends` have data
- Research done: `combined_final_cited_report` has 500+ chars
- Ad creative done: `final_select_ad_copies` has entries
- Images done: `img_artifact_keys` has 3 entries
- Commercial done: `commercial_artifact` has a `gcs_uri`
- Focus group done: `focus_group_evaluation` has text
- Report done: `final_report_with_citations` has text

## Campaign Context (from session state)
- **Brand**: {brand}
- **Product**: {target_product}
- **Target Audience**: {target_audience}
- **Key Selling Points**: {key_selling_points}
- **Commercial Duration**: {commercial_duration}s

If `brand` and `target_product` are populated above (not empty), the campaign is set up and you should proceed directly to gather_trends. If they are empty, ask the user for these details first.
"""
