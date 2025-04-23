from .tools import generate_image, generate_video
from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.adk.tools import ToolContext, LongRunningFunctionTool
from .prompts import (
    image_generation_instructions,
    video_generation_tips,
    # movie_code_generation_example,
)
from google.genai import types

# from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor


image_generation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="image_and_video_generation_agent",
    instruction=image_generation_instructions + video_generation_tips,
    tools=[
        generate_image,
        LongRunningFunctionTool(generate_video),
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    # code_executor=UnsafeLocalCodeExecutor(),
)
