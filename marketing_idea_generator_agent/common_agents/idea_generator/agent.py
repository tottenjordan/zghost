from .prompts import create_brief_prompt
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search


create_new_ideas_agent = Agent(
    model="gemini-2.0-flash-001",
    name="create_new_ideas_agent",
    instruction=create_brief_prompt,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
        # response_modalities=["TEXT", "AUDIO"],
    ),
)
