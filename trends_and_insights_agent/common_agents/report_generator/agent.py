from google.adk.agents import Agent
from google.genai import types

from .tools import generate_research_pdf
from .prompts import AUTO_REPORT_INSTR
from ...utils import MODEL

# from ...prompts import GLOBAL_INSTR


report_generator_agent = Agent(
    model=MODEL,
    name="report_generator_agent",
    description="Generates comprehensive PDF report outlining the campaign guide, trends, insights from web research, and ad creatives.",
    # global_instruction=GLOBAL_INSTR,
    instruction=AUTO_REPORT_INSTR,
    tools=[
        generate_research_pdf,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
)
