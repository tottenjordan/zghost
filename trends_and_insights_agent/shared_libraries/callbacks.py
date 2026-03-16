"""callbacks - currently exploring how these work by observing log output"""

from typing import Dict, Any, Optional
import asyncio
import os, re, json, time
import pandas as pd
import requests
import logging

logging.basicConfig(level=logging.INFO)

from google import genai
from google.genai import types
from google.adk.sessions.state import State
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools import ToolContext

from .config import config, setup_config

ENABLE_LLM_STATUS = os.environ.get("ENABLE_LLM_STATUS", "true").lower() == "true"


# ================================================================
# ui:status_update callbacks for Gemini Enterprise status chips
# ================================================================

TOOL_STATUS_MESSAGES = {
    "get_daily_gtrends": "Fetching today's Google Search trends...",
    "get_youtube_trends": "Fetching trending YouTube videos...",
    "google_search": "Searching the web for insights...",
    "generate_image": "Generating image with Gemini...",
    "generate_video": "Generating video with Veo (this may take a few minutes)...",
    "save_draft_report_artifact": "Generating draft research report...",
    "save_creatives_and_research_report": "Compiling final report...",
    "combined_research_pipeline": "Starting research pipeline...",
    "ad_creative_pipeline": "Starting ad copy generation...",
    "visual_generation_pipeline": "Starting visual concept development...",
    "visual_generator": "Generating images and videos...",
    "evaluate_media_fidelity": "Evaluating image fidelity with Gecko...",
    "transfer_to_agent": "Transferring to next agent...",
    "load_artifacts": "Loading artifacts for display...",
    "preload_memory": "Loading campaign memories...",
    "recall_prior_insights": "Searching memory bank for prior insights...",
    "analyze_commercial_video": "Analyzing commercial video with Gemini vision...",
    "generate_panelist_portrait": "Generating focus group panelist portrait with Imagen 4...",
    "generate_panelist_testimonial": "Creating Ken Burns testimonial video with Chirp voice-over...",
    "concatenate_panelist_videos": "Assembling focus group reel with Lyria background music...",
}

TOOL_DESCRIPTIONS = {
    "get_daily_gtrends": "fetches today's trending Google Search topics",
    "get_youtube_trends": "fetches currently trending YouTube videos",
    "google_search": "searches the web for market research insights on consumer trends and brand positioning",
    "generate_image": "generates a product advertising image using Gemini Flash Image AI",
    "generate_video": "generates a commercial video clip using Veo AI",
    "save_draft_report_artifact": "saves a draft research report as PDF",
    "save_creatives_and_research_report": "compiles the final campaign report",
    "analyze_youtube_videos": "analyzes trending YouTube video content for audience insights and cultural relevance",
    "save_yt_trends_to_session_state": "saves selected YouTube trends",
    "save_search_trends_to_session_state": "saves selected search trends",
    "save_img_artifact_key": "saves image artifact metadata",
    "save_vid_artifact_key": "saves video artifact metadata",
    "save_select_ad_copy": "saves selected ad copy",
    "save_select_visual_concept": "saves selected visual concept",
    "memorize": "saves information to memory",
    "load_artifacts": "loads saved artifacts for display",
    "preload_memory": "loads campaign memories from memory bank",
    "recall_prior_insights": "retrieves historical campaign learnings and audience preferences from memory bank",
    "evaluate_media_fidelity": "evaluates visual brand consistency and product accuracy using Gecko AI scoring",
    "transfer_to_agent": "transfers control to another agent",
    "combined_research_pipeline": "runs the full research pipeline",
    "analyze_commercial_video": "analyzes the commercial video frame-by-frame using Gemini vision for quality, consistency, and brand alignment",
    "generate_panelist_portrait": "generates a realistic AI portrait of a focus group panelist using Imagen 4",
    "generate_panelist_testimonial": "creates a cinematic Ken Burns testimonial video with Chirp HD voice-over matched to the panelist's demographic",
    "concatenate_panelist_videos": "assembles all panelist testimonials into a polished focus group reel with Lyria 2 background music",
}


AGENT_STATUS_MESSAGES = {
    "root_agent": "Planning next steps...",
    "research_orchestrator": "Orchestrating research...",
    "merge_planners": "Merging research findings...",
    "combined_web_evaluator": "Evaluating research quality...",
    "enhanced_combined_searcher": "Conducting follow-up research...",
    "combined_report_composer": "Composing research report...",
    "ad_copy_drafter": "Drafting ad copy ideas...",
    "ad_copy_critic": "Critiquing ad copies...",
    "ad_content_generator_agent": "Orchestrating ad generation...",
    "visual_concept_drafter": "Drafting visual concepts...",
    "visual_concept_critic": "Critiquing visual concepts...",
    "visual_concept_finalizer": "Finalizing visual concepts...",
    "visual_generator": "Preparing to generate visuals...",
    "report_saver_agent": "Saving research report...",  # legacy, now handled by ResearchPipelineOrchestrator
    "fidelity_evaluator": "Evaluating media fidelity with Gecko...",
    "av_editing_studio_agent": "Directing commercial production in AV studio...",
    "commercial_qa_agent": "Evaluating commercial quality with Gecko vision analysis...",
    "focus_group_evaluator_agent": "Assembling virtual focus group panel for evaluation...",
}


def before_model_status_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """Sets ui:status_update before each LLM call so GE shows status during model generation."""
    agent_name = callback_context.agent_name

    # For root_agent (LlmAgent orchestrator), infer the next stage from state
    # Use a counter to vary messages and prevent repetition
    if agent_name == "root_agent":
        state = callback_context.state
        model_call_count = state.get("_root_model_calls", 0) + 1
        callback_context.state["_root_model_calls"] = model_call_count

        # Detailed status based on pipeline completeness
        # Check for actual trend DATA, not just the empty dict wrapper
        _search_trends_raw = state.get("target_search_trends", {})
        _yt_trends_raw = state.get("target_yt_trends", {})
        has_trends = (
            (isinstance(_search_trends_raw, dict) and bool(_search_trends_raw.get("target_search_trends")))
            or (isinstance(_yt_trends_raw, dict) and bool(_yt_trends_raw.get("target_yt_trends")))
        )
        has_research = bool(state.get("combined_final_cited_report")) and len(str(state.get("combined_final_cited_report", ""))) > 100

        # Check for actual ad copy DATA inside the wrapper dict
        _ad_copies_raw = state.get("final_select_ad_copies", {})
        has_ad_copies = (
            isinstance(_ad_copies_raw, dict) and bool(_ad_copies_raw.get("final_select_ad_copies"))
        ) or (isinstance(_ad_copies_raw, list) and len(_ad_copies_raw) > 0)

        # Check for actual image DATA inside the wrapper dict
        # Also check that all images pass Gecko threshold (0.7) — if any fail
        # and haven't exceeded retries, re-enter generate_images for retry
        _img_keys_raw = state.get("img_artifact_keys", {})
        _img_list = (
            _img_keys_raw.get("img_artifact_keys", []) if isinstance(_img_keys_raw, dict) else _img_keys_raw
        ) if _img_keys_raw else []
        _img_count = len(_img_list) if isinstance(_img_list, list) else 0
        _has_enough_images = _img_count >= 3
        _images_need_retry = False
        if _has_enough_images and isinstance(_img_list, list):
            for _idx, _img in enumerate(_img_list):
                if isinstance(_img, dict) and not _img.get("skipped"):
                    _score = _img.get("fidelity_score")
                    _fails = state.get(f"_img_fail_{_idx}", 0)
                    if _score is not None and _score < 0.7 and _fails < 5:
                        _images_need_retry = True
                        break
        has_images = _has_enough_images and not _images_need_retry

        has_commercial = isinstance(state.get("commercial_artifact"), dict) and state.get("commercial_artifact", {}).get("gcs_uri")
        has_focus_group = (bool(state.get("focus_group_evaluation")) and len(str(state.get("focus_group_evaluation", ""))) > 20) or state.get("_focus_group_complete")
        has_final = bool(state.get("final_report_with_citations")) and len(str(state.get("final_report_with_citations", ""))) > 100

        # Helper: force a tool call via tool_config.
        # By default, uses mode="ANY" WITHOUT allowed_function_names so the
        # model must call *some* tool but still thinks about which one —
        # producing visible thought parts in GE/ADK web.
        # Use restrict=True for tools that often get skipped (setup, save).
        def _force_tool(tool_name: str, restrict: bool = False):
            if llm_request.config is None:
                llm_request.config = types.GenerateContentConfig()
            # Preserve thinking config so thoughts are visible
            if llm_request.config.thinking_config is None:
                llm_request.config.thinking_config = types.ThinkingConfig(
                    thinking_budget=8192
                )
            if restrict:
                llm_request.config.tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",
                        allowed_function_names=[tool_name],
                    )
                )
            else:
                llm_request.config.tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",
                    )
                )
            logging.info(f"[MODEL_STATUS] Forcing tool call (hint={tool_name}, restrict={restrict})")

        # After gather_trends runs, cached trends exist but user hasn't picked yet
        has_cached_trends = bool(state.get("_cached_search_trends")) or bool(state.get("_cached_yt_trends"))

        # Check if brand/product are set (needed before gather_trends)
        has_campaign_info = bool(state.get("brand")) and bool(state.get("target_product"))

        if not has_trends and not has_cached_trends and has_campaign_info:
            status_msg = "Analyzing campaign brief and preparing trend discovery..."
            _force_tool("gather_trends")
        elif not has_trends and not has_cached_trends and not has_campaign_info:
            # Campaign info missing — force setup_campaign so LLM extracts from user message
            status_msg = "Setting up campaign details..."
            _force_tool("setup_campaign", restrict=True)
        elif not has_trends and has_cached_trends:
            # Trends fetched but user hasn't selected yet — let model present and wait
            status_msg = "Presenting trend options for your selection..."
        elif not has_research:
            variants = [
                "Synthesizing trend data into a comprehensive research report...",
                "Connecting cultural trends to brand strategy with AI analysis...",
                "Building research insights across Google and YouTube trends...",
            ]
            status_msg = variants[(model_call_count - 1) % len(variants)]
            _force_tool("run_research")
        elif not has_ad_copies:
            status_msg = "Drafting and critiquing ad copy concepts with creative AI..."
            _force_tool("run_ad_creative")
        elif not has_images:
            status_msg = "Generating reference images with Imagen 4 and Gecko quality scoring..."
            _force_tool("generate_images")
        elif not has_commercial:
            status_msg = "Producing commercial video with Veo 3.1 AI video engine..."
            _force_tool("generate_commercial")
        elif not has_focus_group:
            status_msg = "Assembling virtual focus group panel for campaign evaluation..."
            _force_tool("run_focus_group")
        elif not has_final:
            # Force the model to call save_report — all stages done but PDF not saved
            # Use looser check for forcing (any non-empty value counts)
            _has_research_any = bool(state.get("combined_final_cited_report"))
            _has_fg_any = bool(state.get("focus_group_evaluation")) or state.get("_focus_group_complete")
            if _has_research_any and _has_fg_any:
                status_msg = "Compiling final campaign brief with all assets into branded PDF report..."
                _force_tool("save_report", restrict=True)
            else:
                # When reviewing pre-populated state, provide rich stage-specific messages
                review_msgs = [
                    "Reviewing 6000+ character research report across trend analysis and strategic recommendations...",
                    "Analyzing ad creative concepts: trend alignment, audience appeal, and brand integration...",
                    "Evaluating Gecko fidelity scores for product, person, and trend ASSET reference images...",
                    "Reviewing Veo 3.1 commercial: 8-second cinematic spot with reference image composition...",
                    "Analyzing focus group panel responses: creative impact, purchase intent, Go/No-Go verdict...",
                    "Compiling final campaign brief with all assets into branded PDF report...",
                ]
                status_msg = review_msgs[(model_call_count - 1) % len(review_msgs)]
        else:
            status_msg = "Campaign pipeline complete — all deliverables ready for review..."
    else:
        status_msg = AGENT_STATUS_MESSAGES.get(agent_name, f"Working on {agent_name}...")

    callback_context.state["ui:status_update"] = status_msg
    logging.info(f"[MODEL_STATUS] {agent_name}: {status_msg}")


_LLM_STATUS_TIMEOUT_SECONDS = 3.0


async def _async_generate_contextual_status(tool_name: str, args: dict) -> str:
    """Generate a contextual status message using a fast async LLM call."""
    try:
        tool_desc = TOOL_DESCRIPTIONS.get(tool_name, f"runs {tool_name}")
        context_hint = ""
        for key in ("query", "prompt", "agent_name", "topic", "trend"):
            if key in args:
                context_hint = f" Context: {str(args[key])[:100]}"
                break

        client = genai.Client(vertexai=True)
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model="gemini-3-flash-preview",
                contents=f"Tool '{tool_name}' {tool_desc}.{context_hint}",
                config=types.GenerateContentConfig(
                    system_instruction="Generate a single short status message (under 15 words) describing what is happening. Be specific and contextual. Do not use quotes. Example: Searching for Nike summer campaign trends across social media",
                    temperature=0.3,
                    max_output_tokens=30,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            ),
            timeout=_LLM_STATUS_TIMEOUT_SECONDS,
        )
        status = response.text.strip().rstrip(".")
        if status and len(status) < 100:
            return status
    except Exception as e:
        logging.warning(f"[STATUS] LLM status generation failed: {e}")
    return TOOL_STATUS_MESSAGES.get(tool_name, f"Processing {tool_name}...")


async def before_tool_status_callback(
    tool: BaseTool, args: dict, tool_context: ToolContext
) -> Optional[dict]:
    """Sets ui:status_update in session state so Gemini Enterprise renders a status chip."""
    tool_name = tool.name

    # Track tool start time for duration logging
    tool_context.state["_tool_start_ts"] = time.monotonic()
    tool_context.state["_tool_name"] = tool_name

    # Generate contextual status via LLM or fall back to static
    if ENABLE_LLM_STATUS:
        status_msg = await _async_generate_contextual_status(tool_name, args)
    else:
        status_msg = TOOL_STATUS_MESSAGES.get(tool_name, f"Processing {tool_name}...")

    # Enrich transfer_to_agent with target agent name
    if tool_name == "transfer_to_agent" and "agent_name" in args:
        agent_display = args["agent_name"].replace("_", " ").title()
        status_msg = f"Transferring to {agent_display}..."

    logging.info(f"[STATUS] {tool_name}: {status_msg}")

    # Only set ui:status_update — do NOT set ui:thinking_message
    tool_context.state["ui:status_update"] = status_msg
    return None


async def after_tool_status_callback(
    tool: BaseTool, args: dict, tool_context: ToolContext, tool_response: dict
) -> Optional[dict]:
    """Log duration and surface fidelity/generation results as status updates."""
    start_ts = tool_context.state.get("_tool_start_ts")
    tool_name = tool_context.state.get("_tool_name", tool.name)
    if start_ts:
        duration = time.monotonic() - start_ts
        logging.info(f"[TOOL_DURATION] {tool_name} completed in {duration:.1f}s")

    # Surface fidelity evaluation results
    if tool_name == "evaluate_media_fidelity" and isinstance(tool_response, dict):
        score = tool_response.get("score", 0.0)
        passed = tool_response.get("passed", False)
        if tool_response.get("status") == "error":
            status_msg = f"Fidelity evaluation error: {tool_response.get('error', 'unknown')}"
        elif passed:
            status_msg = f"Image fidelity score: {score:.2f}/1.0 — High quality, proceeding"
        else:
            # Include failing verdict details if available
            failing = tool_response.get("failing", [])
            if failing:
                verdict_summary = ", ".join(str(v)[:40] for v in failing[:2])
                status_msg = f"Image fidelity score: {score:.2f}/1.0 — Below threshold, regenerating ({verdict_summary})"
            else:
                status_msg = f"Image fidelity score: {score:.2f}/1.0 — Below threshold, regenerating with improved prompt"
        tool_context.state["ui:status_update"] = status_msg
        logging.info(f"[FIDELITY_STATUS] {status_msg}")

    # Surface failed image generation
    if tool_name == "generate_image" and isinstance(tool_response, dict):
        if tool_response.get("status") != "ok":
            error_detail = tool_response.get("error", "unknown error")
            status_msg = f"Image generation failed ({error_detail}) — retrying with refined prompt"
            tool_context.state["ui:status_update"] = status_msg
            logging.info(f"[GEN_STATUS] {status_msg}")

    return None


def reorder_parts_text_first(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """after_model_callback: reorders parts (text first), preserves thoughts, strips inline_data.

    - Preserves thought parts (parts with thought=True) in their original position
      so GE can render them as thinking indicators
    - Reorders remaining parts so text comes before function_calls (prevents GE blank bubbles)
    - Strips inline_data parts (images/videos already saved as ADK artifacts via
      tool_context.save_artifact(); GE renders those inline natively)
    """
    if (
        llm_response
        and llm_response.content
        and llm_response.content.parts
    ):
        thought_parts = []
        text_parts = []
        func_parts = []
        stripped_count = 0
        for part in llm_response.content.parts:
            if hasattr(part, "inline_data") and part.inline_data is not None:
                stripped_count += 1
                continue
            # Preserve thought parts separately — GE renders these as thinking indicators
            if getattr(part, "thought", False) or getattr(part, "thought_signature", None):
                thought_parts.append(part)
            elif part.text is not None:
                text_parts.append(part)
            else:
                func_parts.append(part)
        if stripped_count:
            logging.info(f"[CALLBACK] Stripped {stripped_count} inline_data part(s) from model response")
        # Order: thoughts first, then text, then function calls
        reordered = thought_parts + text_parts + func_parts
        if reordered:
            llm_response.content.parts = reordered
    return llm_response


# Get the cloud storage bucket from the environment variable
try:
    GCS_BUCKET = os.environ["BUCKET"]
except KeyError:
    raise Exception("BUCKET environment variable not set")


# get initial session state json
SESSION_STATE_JSON_PATH = os.getenv("SESSION_STATE_JSON_PATH", default=None)
logging.info(f"\n\n`SESSION_STATE_JSON_PATH`: {SESSION_STATE_JSON_PATH}\n\n")

# TODO: this is a short term fix for deployment to agent space
if SESSION_STATE_JSON_PATH:
    PROFILE_PATH = "http://raw.githubusercontent.com/tottenjordan/zghost/refs/heads/deployment-fix-july-25/trends_and_insights_agent/shared_libraries/profiles"
    FULL_JSON_PATH = os.path.join(PROFILE_PATH, SESSION_STATE_JSON_PATH)
else:
    FULL_JSON_PATH = None


def _set_initial_states(source: Dict[str, Any], target: State | dict[str, Any]):
    """
    Setting the initial session state given a JSON object of states.

    Args:
        source: A JSON object of states.
        target: The session state object to insert into.
    """
    if setup_config.state_init not in target:
        target[setup_config.state_init] = True
        target["gcs_folder"] = pd.Timestamp.utcnow().strftime("%Y_%m_%d_%H_%M")

        # Per-key check: only set defaults for keys that aren't already populated.
        # This preserves values pre-loaded via create_session(state=...) from the
        # E2E runner or Gemini Enterprise, while filling in any missing keys.
        for key, value in source.items():
            if key not in target or target.get(key) is None:
                target[key] = value

    # Always ensure required template variables have defaults to prevent
    # KeyError in ADK's inject_session_state when processing {var} patterns
    for key, default_value in setup_config.empty_session_state["state"].items():
        if target.get(key) is None:
            target[key] = default_value


def _load_session_state(callback_context: CallbackContext):
    """
    Sets up the initial state.
    Set this as a callback as before_agent_call of the `root_agent`.
    This gets called before the system instruction is constructed.

    Also recovers lost tool outputs from GCS write-through cache.
    On AE, tool_context.state writes in long-running tools are lost when
    waves timeout before the function_response event is persisted. The
    GCS cache provides cross-wave recovery.

    Args:
        callback_context: The callback context.
    """
    data = {}
    if FULL_JSON_PATH:
        if FULL_JSON_PATH.startswith("http"):
            try:
                resp = requests.get(FULL_JSON_PATH)
                data = json.loads(resp.text)
                logging.info(f"\n\nLoading Initial State from URL: {data}\n\n")
            except Exception as e:
                logging.error(f"Error loading state from URL {FULL_JSON_PATH}: {e}")
                data = setup_config.empty_session_state
        else:
            try:
                with open(FULL_JSON_PATH, "r") as f:
                    data = json.load(f)
                logging.info(f"\n\nLoading Initial State from File: {data}\n\n")
            except FileNotFoundError:
                logging.warning(f"File not found at {FULL_JSON_PATH}, using empty state.")
                data = setup_config.empty_session_state
            except Exception as e:
                logging.error(f"Error loading state from {FULL_JSON_PATH}: {e}")
                data = setup_config.empty_session_state
    else:
        data = setup_config.empty_session_state
        logging.info(f"\n\nLoading Initial State (empty): {data}\n\n")

    _set_initial_states(data["state"], callback_context.state)

    # Recover lost tool outputs from GCS write-through cache
    try:
        from ..orchestrator import gcs_state_recover
        recovered = gcs_state_recover(callback_context.state)
        if recovered > 0:
            logging.info(f"[GCS_RECOVERY] Recovered {recovered} state key(s) from GCS cache")
    except Exception as e:
        logging.warning(f"[GCS_RECOVERY] Failed: {e}")


def rate_limit_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    # pylint: disable=unused-argument
    """Callback function that implements a query rate limit.

    Args:
      callback_context: A CallbackContext object representing the active
              callback context.
      llm_request: A LlmRequest object representing the active LLM request.
    """
    now = time.time()
    if "timer_start" not in callback_context.state:
        callback_context.state["timer_start"] = now
        callback_context.state["request_count"] = 1
        logging.debug(
            "rate_limit_callback [timestamp: %i, req_count: 1, " "elapsed_secs: 0]",
            now,
        )
        return

    request_count = callback_context.state["request_count"] + 1
    elapsed_secs = now - callback_context.state["timer_start"]
    logging.debug(
        "rate_limit_callback [timestamp: %i, request_count: %i," " elapsed_secs: %i]",
        now,
        request_count,
        elapsed_secs,
    )

    if request_count > config.rpm_quota:
        delay = config.rate_limit_seconds - elapsed_secs + 1
        if delay > 0:
            logging.debug("Sleeping for %i seconds", delay)
            time.sleep(delay)
        callback_context.state["timer_start"] = now
        callback_context.state["request_count"] = 1
    else:
        callback_context.state["request_count"] = request_count

    return


def campaign_callback_function(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    This sets default values for:
        *   brand
        *   target_audience
        *   target_product
        *   key_selling_points
        *   img_artifact_keys
        *   vid_artifact_keys
        *   target_search_trends
        *   target_yt_trends
        *   final_select_ad_copies
        *   final_select_vis_concepts
    """

    agent_name = callback_context.agent_name
    # invocation_id = callback_context.invocation_id
    # current_state = callback_context.state.to_dict()

    # Check the condition in session state dictionary
    brand = callback_context.state.get("brand")
    target_audience = callback_context.state.get("target_audience")
    target_product = callback_context.state.get("target_product")
    key_selling_points = callback_context.state.get("key_selling_points")
    final_select_ad_copies = callback_context.state.get("final_select_ad_copies")
    final_select_vis_concepts = callback_context.state.get("final_select_vis_concepts")
    img_artifact_keys = callback_context.state.get("img_artifact_keys")
    vid_artifact_keys = callback_context.state.get("vid_artifact_keys")
    target_yt_trends = callback_context.state.get("target_yt_trends")
    target_search_trends = callback_context.state.get("target_search_trends")

    return_content = None  # placeholder for optional returned parts

    if brand is None:
        return_content = "brand"
        callback_context.state["brand"] = ""

    if target_audience is None:
        callback_context.state["target_audience"] = ""
        if return_content is None:
            return_content = "target_audience"
        else:
            return_content += ", target_audience"

    if target_product is None:
        callback_context.state["target_product"] = ""
        if return_content is None:
            return_content = "target_product"
        else:
            return_content += ", target_product"

    if key_selling_points is None:
        callback_context.state["key_selling_points"] = ""
        if return_content is None:
            return_content = "key_selling_points"
        else:
            return_content += ", key_selling_points"

    if final_select_ad_copies is None:
        callback_context.state["final_select_ad_copies"] = {
            "final_select_ad_copies": []
        }
        if return_content is None:
            return_content = "final_select_ad_copies"
        else:
            return_content += ", final_select_ad_copies"

    if final_select_vis_concepts is None:
        callback_context.state["final_select_vis_concepts"] = {
            "final_select_vis_concepts": []
        }
        if return_content is None:
            return_content = "final_select_vis_concepts"
        else:
            return_content += ", final_select_vis_concepts"

    if img_artifact_keys is None:
        callback_context.state["img_artifact_keys"] = {"img_artifact_keys": []}
        if return_content is None:
            return_content = "img_artifact_keys"
        else:
            return_content += ", img_artifact_keys"

    if vid_artifact_keys is None:
        callback_context.state["vid_artifact_keys"] = {"vid_artifact_keys": []}
        if return_content is None:
            return_content = "vid_artifact_keys"
        else:
            return_content += ", vid_artifact_keys"

    if target_search_trends is None:
        callback_context.state["target_search_trends"] = {"target_search_trends": []}
        if return_content is None:
            return_content = "target_search_trends"
        else:
            return_content += ", target_search_trends"

    if target_yt_trends is None:
        callback_context.state["target_yt_trends"] = {"target_yt_trends": []}
        if return_content is None:
            return_content = "target_yt_trends"
        else:
            return_content += ", target_yt_trends"

    if return_content is not None:
        return types.Content(
            parts=[
                types.Part(
                    text=f"Agent {agent_name} setting default values for state variables: \n\n{return_content}."
                )
            ],
            role="model",  # Assign model role to the overriding response
        )

    else:
        return None


def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources and their supported claims from agent events.

    This function processes the agent's `session.events` to extract web source details (URLs,
    titles, domains from `grounding_chunks`) and associated text segments with confidence scores
    (from `grounding_supports`). The aggregated source information and a mapping of URLs to short
    IDs are cumulatively stored in `callback_context.state`.

    Args:
        callback_context (CallbackContext): The context object providing access to the agent's
            session events and persistent state.
    """
    session = callback_context._invocation_context.session
    url_to_short_id = callback_context.state.get("url_to_short_id", {})
    sources = callback_context.state.get("sources", {})
    id_counter = len(url_to_short_id) + 1
    for event in session.events:
        if not (event.grounding_metadata and event.grounding_metadata.grounding_chunks):
            continue
        chunks_info = {}
        for idx, chunk in enumerate(event.grounding_metadata.grounding_chunks):
            if not chunk.web:
                continue
            url = chunk.web.uri
            title = (
                chunk.web.title
                if chunk.web.title != chunk.web.domain
                else chunk.web.domain
            )
            if url not in url_to_short_id:
                short_id = f"src-{id_counter}"
                url_to_short_id[url] = short_id
                sources[short_id] = {
                    "short_id": short_id,
                    "title": title,
                    "url": url,
                    "domain": chunk.web.domain,
                    "supported_claims": [],
                }
                id_counter += 1
            chunks_info[idx] = url_to_short_id[url]
        if event.grounding_metadata.grounding_supports:
            for support in event.grounding_metadata.grounding_supports:
                confidence_scores = support.confidence_scores or []
                chunk_indices = support.grounding_chunk_indices or []
                for i, chunk_idx in enumerate(chunk_indices):
                    if chunk_idx in chunks_info:
                        short_id = chunks_info[chunk_idx]
                        confidence = (
                            confidence_scores[i] if i < len(confidence_scores) else 0.5
                        )
                        text_segment = support.segment.text if support.segment else ""
                        sources[short_id]["supported_claims"].append(
                            {
                                "text_segment": text_segment,
                                "confidence": confidence,
                            }
                        )
    callback_context.state["url_to_short_id"] = url_to_short_id
    callback_context.state["sources"] = sources


def citation_replacement_callback(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Replaces citation tags in a report with Markdown-formatted links.

    Processes 'combined_final_cited_report' from context state, converting tags like
    `<cite source="src-N"/>` into hyperlinks using source information from
    `callback_context.state["sources"]`. Also fixes spacing around punctuation.

    Args:
        callback_context (CallbackContext): Contains the report and source information.

    Returns:
        types.Content: The processed report with Markdown citation links.
    """
    # types.Content: The processed report with Markdown citation links.
    final_report = callback_context.state.get("combined_final_cited_report", "")
    sources = callback_context.state.get("sources", {})

    def tag_replacer(match: re.Match) -> str:
        short_id = match.group(1)
        if not (source_info := sources.get(short_id)):
            logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
            return ""
        display_text = source_info.get("title", source_info.get("domain", short_id))
        return f" [{display_text}]({source_info['url']})"

    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>',
        tag_replacer,
        final_report,
    )
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)
    callback_context.state["research_report_with_citations"] = processed_report
    # return types.Content(parts=[types.Part(text=processed_report)])
    return types.Content(parts=[types.Part(text="PDF report saved to memory 📝 !!")])


def _get_memory_client():
    """Get Memory Bank client and resource name, or (None, None) if not configured."""
    agent_engine_id = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
    if not agent_engine_id:
        return None, None
    import vertexai
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    project_number = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
    location = os.getenv("MEMORY_BANK_LOCATION", "us-central1")
    client = vertexai.Client(project=project, location=location)
    resource_name = f"projects/{project_number}/locations/{location}/reasoningEngines/{agent_engine_id}"
    return client, resource_name


def _save_facts_to_memory(client, resource_name, facts, scope):
    """Save facts to Memory Bank in batches of 5."""
    for i in range(0, len(facts), 5):
        batch = facts[i:i+5]
        client.agent_engines.memories.generate(
            name=resource_name,
            direct_memories_source={"direct_memories": [{"fact": f} for f in batch]},
            scope=scope,
            config={"wait_for_completion": False},
        )
        logging.info(f"Saved batch of {len(batch)} facts to Memory Bank (scope={scope})")


# --- SCOPE SCHEMA ---
# Memory Bank uses scope keys for filtering. Our multi-dimensional schema:
#
# Dimension 1: Campaign Insights (what we learned about brands/audiences)
#   scope: {"user_id": "...", "memory_type": "campaign_insight", "brand": "Tide"}
#
# Dimension 2: Skill Memories (what worked/failed for each pipeline stage)
#   scope: {"user_id": "...", "memory_type": "skill_memory", "skill": "research"}
#   scope: {"user_id": "...", "memory_type": "skill_memory", "skill": "ad_creative"}
#   scope: {"user_id": "...", "memory_type": "skill_memory", "skill": "av_studio"}
#
# Dimension 3: Quality Metrics (track improvement over time)
#   scope: {"user_id": "...", "memory_type": "quality_metric", "skill": "research"}


def save_research_to_memory(callback_context: CallbackContext) -> None:
    """After research completes, save campaign insights AND skill memories."""
    try:
        client, resource_name = _get_memory_client()
        if not client:
            return

        report = callback_context.state.get("combined_final_cited_report", "")
        if not report or len(report) < 100:
            return

        brand = callback_context.state.get("brand", "unknown")
        product = callback_context.state.get("target_product", "unknown")
        audience = callback_context.state.get("target_audience", "unknown")
        user_id = getattr(callback_context, "user_id", "default") or "default"

        # --- Campaign Insights ---
        campaign_facts = []
        ksp = callback_context.state.get("key_selling_points", "")
        if ksp:
            campaign_facts.append(f"{brand} {product} key selling points: {ksp}")

        search_trends = callback_context.state.get("target_search_trends", {})
        yt_trends = callback_context.state.get("target_yt_trends", {})
        if isinstance(search_trends, dict):
            for t in search_trends.get("target_search_trends", []):
                campaign_facts.append(f"Search trend for {brand}: {t.get('title', '')} - {t.get('description', '')}")
        if isinstance(yt_trends, dict):
            for t in yt_trends.get("target_yt_trends", []):
                campaign_facts.append(f"YouTube trend for {brand}: {t.get('title', '')} - {t.get('description', '')}")

        report_summary = report[:500].replace("\n", " ").strip()
        campaign_facts.append(f"Research summary for {brand} {product} (audience: {audience}): {report_summary}")

        _save_facts_to_memory(client, resource_name, campaign_facts, scope={
            "user_id": user_id,
            "memory_type": "campaign_insight",
            "brand": brand,
        })

        # --- Skill Memory: Research ---
        eval_data = callback_context.state.get("combined_research_evaluation", "")
        skill_facts = [
            f"Research pipeline completed for {brand} {product}: report is {len(report)} chars with citations.",
            f"Target audience was '{audience}' — research covered search trends, YouTube trends, and campaign guide.",
        ]
        if eval_data:
            eval_str = json.dumps(eval_data) if isinstance(eval_data, dict) else str(eval_data)
            skill_facts.append(f"Research quality evaluation: {eval_str[:300]}")

        _save_facts_to_memory(client, resource_name, skill_facts, scope={
            "user_id": user_id,
            "memory_type": "skill_memory",
            "skill": "research",
        })

        logging.info(f"Saved {len(campaign_facts)} campaign + {len(skill_facts)} skill insights to Memory Bank")
    except Exception as e:
        logging.warning(f"Memory Bank save failed (non-fatal): {e}")


def save_creative_skill_to_memory(callback_context: CallbackContext) -> None:
    """After ad creative generation, save skill memories about what worked."""
    try:
        client, resource_name = _get_memory_client()
        if not client:
            return

        brand = callback_context.state.get("brand", "unknown")
        product = callback_context.state.get("target_product", "unknown")
        user_id = getattr(callback_context, "user_id", "default") or "default"

        imgs = callback_context.state.get("img_artifact_keys", {})
        vids = callback_context.state.get("vid_artifact_keys", {})
        if isinstance(imgs, dict):
            imgs = imgs.get("img_artifact_keys", [])
        if isinstance(vids, dict):
            vids = vids.get("vid_artifact_keys", [])

        skill_facts = [
            f"Ad creative for {brand} {product}: generated {len(imgs)} images and {len(vids)} videos.",
        ]

        # Record successful image prompts for skill improvement
        for img in (imgs or [])[:3]:
            prompt = img.get("img_prompt", "")
            headline = img.get("headline", "")
            if prompt:
                skill_facts.append(
                    f"Successful image prompt for {brand} (headline: '{headline}'): {prompt[:200]}"
                )

        # Record successful video prompts
        for vid in (vids or [])[:3]:
            prompt = vid.get("vid_prompt", "")
            headline = vid.get("headline", "")
            if prompt:
                skill_facts.append(
                    f"Successful video prompt for {brand} (headline: '{headline}'): {prompt[:200]}"
                )

        # Record ad copy patterns
        copies = callback_context.state.get("final_select_ad_copies", {})
        if isinstance(copies, dict):
            copies = copies.get("final_select_ad_copies", [])
        for copy in (copies or [])[:2]:
            if isinstance(copy, dict):
                skill_facts.append(
                    f"Selected ad copy for {brand}: headline='{copy.get('headline', '')}', "
                    f"body='{str(copy.get('body', ''))[:150]}'"
                )

        _save_facts_to_memory(client, resource_name, skill_facts, scope={
            "user_id": user_id,
            "memory_type": "skill_memory",
            "skill": "ad_creative",
        })

        # Quality metric
        fidelity = callback_context.state.get("fidelity_scores", {})
        if fidelity:
            metric_facts = [
                f"Gecko fidelity scores for {brand} {product}: {json.dumps(fidelity)[:300]}"
            ]
            _save_facts_to_memory(client, resource_name, metric_facts, scope={
                "user_id": user_id,
                "memory_type": "quality_metric",
                "skill": "ad_creative",
            })

        logging.info(f"Saved {len(skill_facts)} creative skill insights to Memory Bank")
    except Exception as e:
        logging.warning(f"Creative skill memory save failed (non-fatal): {e}")



async def after_agent_skill_reflection(callback_context: CallbackContext):
    """After-agent callback that triggers skill self-reflection when NovaStorm is enabled.

    This is the orchestrator for NovaStorm skill evolution. After key pipeline stages
    complete, it triggers self-reflection to analyze what worked, what didn't, and
    how the skill could improve.

    The reflection is stored in Memory Bank for future skill evolution.

    Workflow:
    1. Check if NovaStorm is enabled
    2. Identify which skill just completed
    3. Gather execution data (tools called, outputs, critiques)
    4. Trigger reflection via skill_evolution.reflect_on_execution()
    5. Save results to Memory Bank
    """
    # Check if NovaStorm is enabled
    enabled = os.environ.get("NOVASTORM_ENABLED", "").lower() == "true"
    if not enabled:
        enabled = callback_context.state.get("novastorm_enabled", False)

    if not enabled:
        return

    agent_name = callback_context.agent_name

    # Map agent names to skill names for reflection
    SKILL_MAP = {
        "research_orchestrator": "research",
        "combined_report_composer": "research",
        "report_saver_agent": "research",
        "ad_content_generator_agent": "ad_creative",
        "ad_creative_pipeline": "ad_creative",
        "creative_production_orchestrator": "ad_creative",
        "visual_generator": "ad_creative",
        "av_editing_studio_agent": "av_studio",
        "av_studio_agent": "av_studio",
        "focus_group_evaluator_agent": "focus_group",
        "focus_group_agent": "focus_group",
    }

    skill_name = SKILL_MAP.get(agent_name)
    if not skill_name:
        return  # Not a skill we track

    # Import skill evolution here to avoid circular imports
    from .skill_evolution import reflect_on_execution, save_skill_dna

    logging.info(f"[NovaStorm] Triggering reflection for skill '{skill_name}' after {agent_name} completed")

    try:
        # Gather execution data based on skill type
        tool_trajectory = ""
        output = ""
        critique = ""

        if skill_name == "research":
            # Research skill: track report generation
            report = callback_context.state.get("combined_final_cited_report", "")
            eval_data = callback_context.state.get("combined_research_evaluation", "")

            output = report[:1000] if report else "No report generated"
            tool_trajectory = f"Research pipeline completed. Report length: {len(report)} chars. Evaluation: {str(eval_data)[:300]}"

            # Get sources/citations as quality signal
            sources = callback_context.state.get("sources", {})
            critique = f"Generated {len(sources)} sources. Report has {report.count('cite')} citations."

        elif skill_name == "ad_creative":
            # Ad creative skill: track images/videos generated
            imgs = callback_context.state.get("img_artifact_keys", {})
            vids = callback_context.state.get("vid_artifact_keys", {})

            if isinstance(imgs, dict):
                imgs = imgs.get("img_artifact_keys", [])
            if isinstance(vids, dict):
                vids = vids.get("vid_artifact_keys", [])

            output = f"Generated {len(imgs or [])} images and {len(vids or [])} videos"
            tool_trajectory = f"Ad creative pipeline: {len(imgs or [])} images, {len(vids or [])} videos"

            # Get fidelity scores as quality signal
            fidelity = callback_context.state.get("fidelity_scores", {})
            if fidelity:
                critique = f"Fidelity scores: {str(fidelity)[:200]}"
            else:
                critique = "No fidelity evaluation available"

        elif skill_name == "av_studio":
            # AV studio skill: track commercial generation
            commercial = callback_context.state.get("commercial_artifact", "")
            duration = callback_context.state.get("commercial_duration", 30)

            output = f"Generated {duration}s commercial: {commercial}"
            tool_trajectory = f"AV studio pipeline: {duration}s commercial with narration and music"
            critique = "Commercial generation completed"

        elif skill_name == "focus_group":
            # Focus group skill: track feedback quality
            feedback = callback_context.state.get("focus_group_feedback", "")
            output = feedback[:1000] if feedback else "No feedback generated"
            tool_trajectory = "Focus group pipeline: diverse panel feedback"
            critique = f"Feedback length: {len(feedback)} chars"

        # Skip reflection if no meaningful output
        if not output or output.startswith("No "):
            logging.info(f"[NovaStorm] Skipping reflection for {skill_name} — no output generated")
            return

        # Get current instructions from state or use empty string
        instructions = callback_context.state.get(f"{skill_name}_instructions", "")

        # Perform reflection
        skill_dna = reflect_on_execution(
            skill_name=skill_name,
            instructions=instructions,
            tool_trajectory=tool_trajectory,
            output=output,
            critique=critique,
        )

        # Save to Memory Bank
        user_id = getattr(callback_context, "user_id", "default") or "default"
        saved = save_skill_dna(skill_dna, user_id)

        if saved:
            logging.info(
                f"[NovaStorm] Reflection complete for {skill_name}: "
                f"score={skill_dna.score}/10, saved to Memory Bank"
            )
        else:
            logging.warning(f"[NovaStorm] Reflection complete for {skill_name} but Memory Bank save failed")

        # Store in state for visibility
        callback_context.state[f"{skill_name}_reflection"] = {
            "score": skill_dna.score,
            "improvements": skill_dna.suggested_improvements,
            "version": skill_dna.version,
        }

    except Exception as e:
        logging.error(f"[NovaStorm] Skill reflection failed for {skill_name}: {e}")
        # Non-fatal — don't block agent execution
