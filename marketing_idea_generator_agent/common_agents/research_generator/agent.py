from google.adk.agents import Agent
from google.genai import types

from .tools import generate_research_pdf
from .prompts import prepare_research_report_instructions

research_generation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="research_generation_agent",
    instruction=prepare_research_report_instructions,
    tools=[
        generate_research_pdf,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
)
