from .tools import generate_image, generate_video
from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.adk.tools import LongRunningFunctionTool
from .prompts import (
    image_generation_instructions,
    video_generation_tips,
    broad_instructions,
)
from google.genai import types


image_generation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="image_generation_agent",
    instruction=broad_instructions
    + image_generation_instructions
    + video_generation_tips,
    tools=[
        generate_image,
        LongRunningFunctionTool(generate_video),
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.5,
    ),
)
