import logging

logging.basicConfig(level=logging.INFO)
from typing import Dict, Any, Optional

from google.genai import types
from google.adk.agents import Agent, LlmAgent
from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.agent_tool import AgentTool
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext

from .prompts import GUIDE_DATA_EXTRACT_INSTR, GUIDE_DATA_GEN_INSTR
from ...shared_libraries import callbacks, schema_types
from ...utils import MODEL

# from ...prompts import GLOBAL_INSTR


campaign_guide_data_extract_agent = LlmAgent(
    model=MODEL,
    name="campaign_guide_data_extract_agent",
    description="Captures campaign guide provided by user.",
    instruction=GUIDE_DATA_EXTRACT_INSTR,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=schema_types.json_response_config,
    output_schema=schema_types.MarketingCampaignGuide,
    output_key="campaign_guide",
    # after_agent_callback=callbacks.modify_output_after_agent,
    # after_tool_callback=callbacks.campaign_callback_function,
)

campaign_guide_data_generation_agent = LlmAgent(
    model=MODEL,
    name="campaign_guide_data_generation_agent",
    description="Extracts, structures, and summarizes key information from marketing campaign guides (provided as URLs, PDFs, or text).",
    instruction=GUIDE_DATA_GEN_INSTR,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    tools=[
        AgentTool(agent=campaign_guide_data_extract_agent),
        # call_extract_campaign_guide_agent,
    ],
    # before_agent_callback=callbacks.before_agent_get_user_file,
    # before_model_callback=simple_before_model_modifier,
    # after_tool_callback=callbacks.simple_after_tool_modifier,
    # after_model_callback=callbacks.simple_after_model_modifier,
    # after_agent_callback=callbacks.modify_output_after_agent,
)

"""
An `invocation` in ADK represents the entire process triggered by a single user query and continues until the agent has finished processing 
    and has no more events to generate, returning control back to the user. 
    It's the complete cycle of agent execution in response to a user input.
    It's a crucial concept for managing the agent's execution, maintaining context, and orchestrating interactions within a session.
"""
