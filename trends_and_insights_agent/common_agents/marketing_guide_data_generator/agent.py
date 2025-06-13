from google.genai import types
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from ...shared_libraries.types import MarketingCampaignGuide
from ...prompts import global_instructions
from ...utils import MODEL

from .prompts import guide_data_extraction_instructions


campaign_guide_data_generation_agent = Agent(
    model=MODEL,
    name="campaign_guide_data_generation_agent",
    instruction=guide_data_extraction_instructions,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    output_schema=MarketingCampaignGuide,
    output_key="campaign_guide",
)
