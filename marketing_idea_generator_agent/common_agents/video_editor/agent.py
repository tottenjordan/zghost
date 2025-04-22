from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.adk.tools import ToolContext, LongRunningFunctionTool
from .prompts import (
    movie_creation_instructions,
    movie_code_generation_example,
)
from google.genai import types

from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor


video_editor_agent = Agent(
    model="gemini-2.5-pro-exp-03-25",
    name="video_editor_agent",
    instruction=movie_creation_instructions + movie_code_generation_example,
    tools=[
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    code_executor=UnsafeLocalCodeExecutor(),
)