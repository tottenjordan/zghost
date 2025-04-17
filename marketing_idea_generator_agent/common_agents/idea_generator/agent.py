from .prompts import create_brief_prompt, youtube_url_instructions
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search
from .tools import (
    query_web,
    # perform_google_search,
    # extract_main_text_from_url,
    analyze_youtube_videos,
    query_youtube_api,
)

official_tooling = [google_search]
tools = [
    # perform_google_search,
    # extract_main_text_from_url,
    analyze_youtube_videos,
    query_youtube_api,
    query_web,
]
create_new_ideas_agent = Agent(
    model="gemini-2.0-flash-001",
    name="create_new_ideas_agent",
    instruction=create_brief_prompt + youtube_url_instructions,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
