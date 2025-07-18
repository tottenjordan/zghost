import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types, Client
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from .prompts import GUIDE_DATA_EXTRACT_INSTR, GUIDE_DATA_GEN_INSTR
from ...shared_libraries import schema_types
from ...shared_libraries.config import config

client = Client()


campaign_guide_data_extract_agent = LlmAgent(
    model=config.worker_model,
    name="campaign_guide_data_extract_agent",
    description="Captures campaign details if user uploads PDF.",
    instruction=GUIDE_DATA_EXTRACT_INSTR,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=schema_types.json_response_config,
    output_schema=schema_types.MarketingCampaignGuide,
    output_key="campaign_guide",
)

campaign_guide_data_generation_agent = LlmAgent(
    model=config.worker_model,
    name="campaign_guide_data_generation_agent",
    description="Extracts and stores key information from marketing campaign guides (PDFs).",
    instruction=GUIDE_DATA_GEN_INSTR,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    tools=[
        AgentTool(agent=campaign_guide_data_extract_agent),
    ],
)
