from .prompts import unified_insights_prompt
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import LongRunningFunctionTool
from ...prompts import global_instructions
# from google.adk.tools import google_search
from ...tools import (
    call_insights_generation_agent,
    query_youtube_api,
    query_web,
    analyze_youtube_videos,
)
from ...utils import MODEL

tools = [
    LongRunningFunctionTool(analyze_youtube_videos),
    query_youtube_api,
    query_web,
    call_insights_generation_agent,
]
web_researcher_agent = Agent(
    model=MODEL,
    name="web_researcher_agent",
    global_instruction=global_instructions,
    instruction=unified_insights_prompt,
    tools=tools,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
