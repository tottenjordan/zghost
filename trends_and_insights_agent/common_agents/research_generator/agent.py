from google.adk.agents import Agent
from google.genai import types

from .tools import generate_research_pdf
from .prompts import prepare_research_report_instructions
from ...prompts import global_instructions
from ...utils import MODEL


research_generation_agent = Agent(
    model=MODEL,
    name="research_generation_agent",
    global_instruction=global_instructions,
    instruction=prepare_research_report_instructions,
    tools=[
        generate_research_pdf,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
)
