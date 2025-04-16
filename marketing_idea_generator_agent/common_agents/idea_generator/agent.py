from .prompts import create_brief_prompt, youtube_analysis_prompt
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search
from .tools import (
    perform_google_search,
    extract_main_text_from_url,
    analyze_youtube_videos,
)

official_tooling = [google_search]
tools = [perform_google_search, extract_main_text_from_url, analyze_youtube_videos]
create_new_ideas_agent = Agent(
    model="gemini-2.0-flash-001",
    name="create_new_ideas_agent",
    instruction=create_brief_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
