from google.adk.agents import Agent
from .prompts import guide_data_extraction_instructions
from .tools import (
    # get_marketing_guide,
    MarketingCampaignGuide,
)
from google.genai import types
from ...prompts import global_instructions

# brief_data_generation_agent
campaign_guide_data_generation_agent = Agent(
    model="gemini-2.0-flash",
    name="campaign_guide_data_generation_agent",
    global_instruction=global_instructions,
    instruction=guide_data_extraction_instructions,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    output_schema=MarketingCampaignGuide,
    output_key="campaign_guide",
)
