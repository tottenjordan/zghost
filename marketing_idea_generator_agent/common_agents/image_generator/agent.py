from .tools import generate_image
from google.adk.agents import Agent
from google.adk.tools import load_artifacts

from .prompts import image_generation_instructions
from google.genai import types


image_generation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="image_generation_agent",
    instruction=image_generation_instructions,
    tools=[generate_image, load_artifacts],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
        # response_modalities=["TEXT", "AUDIO"],
    ),
)
