from google.adk.agents import Agent
from .prompts import brief_data_extraction_instructions
from .tools import get_marketing_brief, MarketingCampaignBrief
from google.genai import types


brief_data_generation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="brief_data_generation_agent",
    instruction=brief_data_extraction_instructions,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    # output_schema=MarketingCampaignBrief,
    output_key="campaign_brief",
)
