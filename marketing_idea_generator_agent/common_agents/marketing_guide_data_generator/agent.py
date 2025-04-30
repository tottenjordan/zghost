from google.adk.agents import Agent
from .prompts import guide_data_extraction_instructions
from .tools import (
    # get_marketing_guide, 
    MarketingCampaignGuide
)
from google.genai import types

# brief_data_generation_agent
campaign_guide_data_generation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="campaign_guide_data_generation_agent",
    instruction=guide_data_extraction_instructions,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    output_schema=MarketingCampaignGuide,
    output_key="campaign_guide",
)
