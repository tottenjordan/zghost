from google.adk.agents import Agent
from google.genai import types

from .tools import generate_research_pdf
from .prompts import AUTO_REPORT_INSTR
from ...prompts import global_instructions
from ...utils import MODEL


report_generator_agent = Agent(
    model=MODEL,
    name="report_generator_agent",
    global_instruction=global_instructions,
    instruction=AUTO_REPORT_INSTR,
    tools=[
        generate_research_pdf,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
)
