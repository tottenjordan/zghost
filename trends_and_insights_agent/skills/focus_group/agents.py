from google.genai import types
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools.base_tool import BaseTool
from google.adk.tools import ToolContext

from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from ...shared_libraries.disclosure import disclose_capabilities

from .tools import analyze_commercial_video, generate_panelist_portrait, generate_panelist_testimonial, concatenate_panelist_videos
from .prompts import FOCUS_GROUP_INSTR


async def _focus_group_before_tool(
    tool: BaseTool, args: dict, tool_context: ToolContext
) -> dict | None:
    """Before-tool callback for focus group — allows all tools to run."""
    return None  # Let all tools run normally


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
    ],
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    before_tool_callback=_focus_group_before_tool,
    before_model_callback=[callbacks.before_model_status_callback, callbacks.rate_limit_callback],
)
