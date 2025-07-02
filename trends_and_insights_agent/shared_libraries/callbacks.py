"""callbacks - currently exploring how these work by observing log output"""

import logging

logging.basicConfig(level=logging.INFO)
from typing import Dict, Any, Optional
from collections import defaultdict

from google.genai import types
from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext


# TODO: not saving artifact correctly
async def before_agent_get_user_file(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Checks for user-uploaded file before the agent runs.

    If file found in user's message, this callback processes it, then
    saves it as an artifact: `user_uploaded_campaign_guide.pdf`.
    At this time, we are only accepting campaign guides in PDF format.
    If no file is found, it returns None, allowing the agent to proceed normally.

    Returns:
        dict: confirmation message to the user
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
    artifact_key = "campaign_guide.pdf"
    file_bytes = part.inline_data.data
    file_type = part.inline_data.mime_type

    # confirm file_type is pdf or png, else let user know the expected type
    if file_type != "application/pdf":
        issue_message = f"The file you provided is of type {file_type} which is not supported here.  Please provide PDF."
        response = types.Content(parts=[types.Part(text=issue_message)], role="model")
        return response

    # create & save artifact
    artifact = types.Part.from_bytes(data=file_bytes, mime_type="application/pdf")
    version = await callback_context.save_artifact(
        filename=artifact_key, artifact=artifact
    )
    callback_context.state["artifact_keys"]["b4_agent_user_file_cb"] = artifact_key

    # Formulate a confirmation message
    confirmation_message = (
        f"Successfully processed your uploaded file.\n\n"
        f"It's now stored as artifact with key: "
        f"'{artifact_key}' (version: {version}, size: {len(file_bytes)} bytes).\n\n"
    )
    response = types.Content(
        parts=[types.Part(text=confirmation_message)], role="model"
    )
    return response


def campaign_callback_function(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    This sets default values for:
        *   campaign_guide
        *   target_search_trends
        *   target_yt_trends
        *   artifact_keys
    """

    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()

    # Check the condition in session state dictionary
    artifact_keys = callback_context.state.get("artifact_keys")
    campaign_guide = callback_context.state.get("campaign_guide")
    target_yt_trends = callback_context.state.get("target_yt_trends")
    target_search_trends = callback_context.state.get("target_search_trends")

    return_content = None  # placeholder for optional returned parts

    if campaign_guide is None:
        return_content = "campaign_guide"
        callback_context.state["campaign_guide"] = "not yet populated"

    if artifact_keys is None:
        callback_context.state["artifact_keys"] = {}
        if return_content is None:
            return_content = "artifact_keys"
        else:
            return_content += ", artifact_keys"

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


def modify_output_after_agent(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Logs exit from an agent and checks 'add_concluding_note' in session state.
    If True, returns new Content to *replace* the agent's original output.
    If False or not present, returns None, allowing the agent's original output to be used.
    """
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()
    logging.info(f"\n\n ## JT DEBUGGING - BEGIN ## \n\n")
    logging.info(f"\n\n --- `modify_output_after_agent` --- \n\n")
    logging.info(f"\n\n[Callback] Exiting agent: {agent_name} (Inv: {invocation_id})\n")
    logging.info(f"\n\n[Callback] Current State: {current_state}\n")
    logging.info(f"\n\n ## JT DEBUGGING - END ## \n\n")
    return None


def simple_after_model_modifier(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    agent_name = callback_context.agent_name

    logging.info(f"\n\n ## JT DEBUGGING - BEGIN ## \n\n")
    logging.info(f"\n\n --- `simple_after_model_modifier` --- \n\n")
    logging.info(f"\n\n[Callback] After model call for agent: {agent_name}\n")
    if llm_response:
        logging.info(f"\n\n[Callback] llm_response : {llm_response}\n")

        if llm_response.content.parts:
            # logging.info(
            #     f"\n\n[Callback] llm_response.content: {llm_response.content}\n"
            # )
            logging.info(
                f"\n\n[Callback] llm_response.content.parts: {llm_response.content.parts}\n"
            )
            if llm_response.content.parts[0].text:
                original_text = llm_response.content.parts[0].text
                logging.info(
                    f"\n\n[Callback] Inspected original response text: '{original_text[:100]}...'"
                )  # Log snippet
            elif llm_response.content.parts[0].function_call:
                logging.info(
                    f"\n\n[Callback] function_call: '{llm_response.content.parts[0].function_call}' \n"
                )
                logging.info(
                    f"\n\n[Callback] function_call: '{llm_response.content.parts[0].function_call.args}' \n"
                )
                logging.info(
                    f"\n\n[Callback] Inspected response: Contains function call '{llm_response.content.parts[0].function_call.name}'. No text modification."
                )

                return None  # Don't modify tool calls in this example
            else:
                logging.info(
                    "\n\n[Callback] Inspected response: No text content found."
                )
                return None
        else:
            logging.info(
                "\n\n[Callback] Inspected llm_response: No text content found.\n"
            )
    else:
        logging.info("\n\n[Callback] callback contex: No text `llm_response` found.\n")
    logging.info(f"\n\n ## JT DEBUGGING - END ## \n\n")
    return None


def simple_after_tool_modifier(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """Inspects/modifies the tool result after execution."""

    agent_name = tool_context.agent_name
    tool_name = tool.name
    logging.info(f"\n\n ## JT DBUGGING - BEGIN ## \n\n")
    logging.info(f"\n\n --- `simple_after_tool_modifier` --- \n\n")
    logging.info(
        f"[Callback] After tool call for tool '{tool_name}' in agent '{agent_name}'\n"
    )
    logging.info(f"\n\n[Callback] Args used: {args}\n")
    logging.info(f"\n\n[Callback] Original tool_response: {tool_response}\n")
    original_result_value = tool_response
    if tool_name == "campaign_guide_data_extract_agent":
        tool_context.state["campaign_guide"] = campaign_guide_state
        logging.info(
            f"\n\nFound tool name: {tool_name} for `campaign_guide_data_extract_agent` tool\n"
        )
    logging.info(f"\n\n ## JT DBUGGING - END ## \n\n")
    return {"status": "ok"}
