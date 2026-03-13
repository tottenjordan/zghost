import pathlib

from google.genai import types
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools.skill_toolset import SkillToolset

from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from ...skills.skill_loader import load_skill_from_dir
from .tools import analyze_commercial_video
from .prompts import FOCUS_GROUP_INSTR

# Load this skill's own SKILL.md for self-contained documentation
_skill_dir = pathlib.Path(__file__).parent
_skill = load_skill_from_dir(_skill_dir)
_skill_toolset = SkillToolset(skills=[_skill])

focus_group_evaluator_agent = Agent(
    model=config.critic_model,
    name="focus_group_evaluator_agent",
    description=(
        "Analyzes a 30-second commercial video with Gemini vision and "
        "simulates a focus group reviewing it for quality, consistency, "
        "trend relevance, and audience uplift potential."
    ),
    instruction=FOCUS_GROUP_INSTR,
    tools=[analyze_commercial_video, _skill_toolset],
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    before_model_callback=callbacks.rate_limit_callback,
)
