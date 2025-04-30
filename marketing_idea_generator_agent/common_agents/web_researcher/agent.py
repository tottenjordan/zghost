from google.genai import types
from google.adk.agents import Agent

web_researcher_agent = Agent(
    model="gemini-2.0-flash-001",
    name="web_researcher_agent",
    instruction=XXXX,
    tools=XXXX,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)