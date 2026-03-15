import pathlib

from google.genai import types
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools.skill_toolset import SkillToolset

from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from ...shared_libraries.disclosure import disclose_capabilities
from ...skills.skill_loader import load_skill_from_dir
from google.adk.tools.base_tool import BaseTool
from google.adk.tools import ToolContext

from .tools import analyze_commercial_video, generate_panelist_portrait, generate_panelist_testimonial, concatenate_panelist_videos
from .prompts import FOCUS_GROUP_INSTR


async def _focus_group_before_tool(
    tool: BaseTool, args: dict, tool_context: ToolContext
) -> dict | None:
    """Before-tool callback for focus group — allows all tools to run.

    Previously skipped portrait/testimonial in autopilot mode, but these are
    now critical for the CMO-impressive demo experience (Ken Burns + Lyria music).
    """
    return None  # Let all tools run normally

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
    tools=[
        analyze_commercial_video,
        generate_panelist_portrait,
        generate_panelist_testimonial,
        concatenate_panelist_videos,
        disclose_capabilities,
        _skill_toolset,
    ],
    output_key="focus_group_evaluation",
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    before_tool_callback=_focus_group_before_tool,
    before_model_callback=[callbacks.before_model_status_callback, callbacks.rate_limit_callback],
    after_agent_callback=callbacks.after_agent_skill_reflection,
)
