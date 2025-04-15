from .prompts import create_brief_prompt
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search
from .tools import perform_google_search, extract_main_text_from_url

official_tooling = [google_search]
tools = [perform_google_search, extract_main_text_from_url]
create_new_ideas_agent = Agent(
    model="gemini-2.0-flash-001",
    name="create_new_ideas_agent",
    instruction=create_brief_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(api_version='v1beta1'),
        temperature=1.0,
        # response_modalities=["TEXT", "AUDIO"],
    ),
)
