from .tools import generate_image, generate_video
from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.adk.tools import LongRunningFunctionTool
from .prompts import unified_image_video_instructions
# (
    # image_generation_instructions,
    # video_generation_tips,
    # broad_instructions,
    # unified_image_video_instructions 
# )
from google.genai import types


ad_content_generator_agent = Agent(
    model="gemini-2.0-flash-001",
    name="ad_content_generator_agent",
    instruction=unified_image_video_instructions,
    tools=[
        generate_image,
        LongRunningFunctionTool(generate_video),
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.5,
    ),
)
