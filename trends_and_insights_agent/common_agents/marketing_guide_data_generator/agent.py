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

from ...shared_libraries.types import MarketingCampaignGuide, json_response_config
from .prompts import GUIDE_DATA_EXTRACT_INSTR, GUIDE_DATA_GEN_INSTR
from ...utils import MODEL, campaign_callback_function

# from ...tools import call_campaign_guide_agent
# from ...prompts import GLOBAL_INSTR


campaign_guide_data_extract_agent = LlmAgent(
    model=MODEL,
    name="campaign_guide_data_extract_agent",
    description="Captures campaign guide provided by user.",
    instruction=GUIDE_DATA_EXTRACT_INSTR,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=json_response_config,
    output_schema=MarketingCampaignGuide,
    output_key="campaign_guide",
    after_agent_callback=campaign_callback_function,
    # before_model_callback=simple_before_model_modifier,
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
    # after_agent_callback=save_campaign_guide_to_session_state,
    # after_tool_callback=simple_after_tool_modifier,  # Assign the callback
    # before_model_callback=simple_before_model_modifier,  # Assign the function here
)
