from google.adk.agents import Agent
from .prompts import brief_data_extraction_instructions
from .tools import get_marketing_brief, MarketingCampaignBrief
from google.genai import types


brief_data_generation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="brief_data_generation_agent",
    instruction=brief_data_extraction_instructions,
    tools=[get_marketing_brief],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        # response_modalities=["TEXT", "AUDIO"],
    ),
    # output_schema=MarketingCampaignBrief,
    # disallow_transfer_to_parent=True,
)
