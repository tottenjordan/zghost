from .tools import generate_image, generate_video
from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.adk.tools import LongRunningFunctionTool
from .prompts import AUTO_CREATIVE_INSTR
from google.genai import types
from ...prompts import global_instructions
from ...utils import MODEL


ad_content_generator_agent = Agent(
    model=MODEL,
    name="ad_content_generator_agent",
    instruction=AUTO_CREATIVE_INSTR,
    tools=[
        generate_image,
        generate_video,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.5,
    ),
)
