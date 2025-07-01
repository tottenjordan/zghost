import logging

logging.basicConfig(level=logging.INFO)
from typing import Dict, Any, Optional

from google.genai import types, Client
from google.adk.tools import ToolContext
from google.adk.agents import Agent, LlmAgent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.agent_tool import AgentTool
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext

from .prompts import GUIDE_DATA_EXTRACT_INSTR, GUIDE_DATA_GEN_INSTR
from ...shared_libraries import callbacks, schema_types
from ...utils import MODEL

client = Client()

# TODO: add support for URLs and user inputs

async def process_toolbox_output(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> str:  # Optional[Dict]:
    """
    Inspects/modifies the tool result after execution.
    """

    # get tool response information
    agent_name = tool_context.agent_name
    response = tool_response  # .get("result", "")
    logging.info(f"\n\n ## JT DEBUGGING - BEGIN ## \n\n")
    logging.info(f"--- `process_toolbox_output` ---")
    logging.info(f"\n\n agent_name: {agent_name}")

    if tool.name == "campaign_guide_data_extract_agent":
        logging.info(f"\n\n tool.name: {tool.name}")
        logging.info(f"\n\n response: {response} .\n\n")
    # passthrough response
    return None


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
)

campaign_guide_data_generation_agent = LlmAgent(
    model=MODEL,
    name="campaign_guide_data_generation_agent",
    description="Extracts and stores key information from marketing campaign guides (PDFs).",
    instruction=GUIDE_DATA_GEN_INSTR,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    tools=[
        AgentTool(agent=campaign_guide_data_extract_agent),
    ],
    after_tool_callback=process_toolbox_output,
)
