"""callbacks - currently exploring how these work by observing log output"""

import os, re, json, time, uuid
import pandas as pd
import requests
import logging

logging.basicConfig(level=logging.INFO)
from typing import Dict, Any, Optional

from google.genai import types
from google.adk.sessions.state import State
from google.adk.models.llm_request import LlmRequest
from google.adk.agents.callback_context import CallbackContext

from .config import config, setup_config


# get initial session state json
SESSION_STATE_JSON_PATH = os.getenv("SESSION_STATE_JSON_PATH", default=None)
logging.info(f"\n\n`SESSION_STATE_JSON_PATH`: {SESSION_STATE_JSON_PATH}\n\n")

# TODO: this is a short term fix for deployment to agent space
if SESSION_STATE_JSON_PATH:
    PROFILE_PATH = "http://raw.githubusercontent.com/tottenjordan/zghost/refs/heads/deployment-fix-july-25/trends_and_insights_agent/shared_libraries/profiles"
    FULL_JSON_PATH = os.path.join(PROFILE_PATH, SESSION_STATE_JSON_PATH)
else:
    FULL_JSON_PATH = None

# Adjust these values to limit the rate at which the agent
# queries the LLM API.
RATE_LIMIT_SECS = config.rate_limit_seconds
RPM_QUOTA = config.rpm_quota


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

        target.update(source)


def _load_session_state(callback_context: CallbackContext):
    """
    Sets up the initial state.
    Set this as a callback as before_agent_call of the `root_agent`.
    This gets called before the system instruction is constructed.

    Args:
        callback_context: The callback context.
    """
    data = {}
    if FULL_JSON_PATH:
        resp = requests.get(FULL_JSON_PATH)
        data = json.loads(resp.text)
        logging.info(f"\n\nLoading Initial State: {data}\n\n")
    else:
        data = setup_config.empty_session_state
        logging.info(f"\n\nLoading Initial State (empty): {data}\n\n")

    _set_initial_states(data["state"], callback_context.state)


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

    if request_count > RPM_QUOTA:
        delay = RATE_LIMIT_SECS - elapsed_secs + 1
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
    """

    agent_name = callback_context.agent_name
    # invocation_id = callback_context.invocation_id
    # current_state = callback_context.state.to_dict()

    # Check the condition in session state dictionary
    brand = callback_context.state.get("brand")
    target_audience = callback_context.state.get("target_audience")
    target_product = callback_context.state.get("target_product")
    key_selling_points = callback_context.state.get("key_selling_points")
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
    callback_context.state["final_report_with_citations"] = processed_report
    # return types.Content(parts=[types.Part(text=processed_report)])
    return types.Content(parts=[types.Part(text="PDF report saved to memory 📝 !!")])


# TODO: add logic for processing PDF contents for session state
async def before_agent_get_user_file(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Checks for a user-uploaded file before the agent runs.

    If a file is found in the user's message, this callback processes it,
    converts it to a PNG (if it's a PDF), and saves it as an artifact named
    'user_uploaded_file'. It then returns a direct confirmation message to the
    user and halts further agent processing for the current turn.

    If no file is found, it returns None, allowing the agent to proceed normally.
    """

    parts = []
    if callback_context.user_content and callback_context.user_content.parts:
        parts = [
            p for p in callback_context.user_content.parts if p.inline_data is not None
        ]

    # if no file then continue to agent by returning empty
    if not parts:
        return None

    # if file then save as artifact
    part = parts[-1]
    if part.inline_data and part.inline_data.data and part.inline_data.mime_type:
        artifact_key = "user_uploaded_file"
        file_bytes = part.inline_data.data
        file_type = part.inline_data.mime_type

        # confirm file_type is pdf, else let user know the expected type
        if file_type not in ["application/pdf"]:
            issue_message = f"The file you provided is of type {file_type} which is not supported here. Please provide a PDF."
            response = types.Content(
                parts=[types.Part(text=issue_message)], role="model"
            )
            return response

        # create & save artifact
        artifact = types.Part.from_bytes(data=file_bytes, mime_type=file_type)
        version = await callback_context.save_artifact(
            filename=artifact_key, artifact=artifact
        )
        callback_context.state["user_document_artifact_key"] = artifact_key

    # Formulate a confirmation message
    confirmation_message = (
        f"Thank you! I've successfully processed your uploaded file.\n\n"
        f"It's now stored as an artifact with key "
        f"'{artifact_key}' (version: {version}, size: {len(file_bytes)} bytes).\n\n"
        f"What would you like to do with it?"
    )

    response = types.Content(
        parts=[types.Part(text=confirmation_message)], role="model"
    )

    return response
