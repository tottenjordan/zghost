from google.genai import types
from google.adk.agents import Agent

from ...tools import query_web
from .tools import call_product_insights_generation_agent
from .prompts import (
    unified_product_insights_prompt,
    # product_insights_generation_prompt
)

tools = [
    query_web,
    call_product_insights_generation_agent,
]

web_researcher_agent = Agent(
    model="gemini-2.0-flash-001",
    name="web_researcher_agent",
    instruction=unified_product_insights_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)