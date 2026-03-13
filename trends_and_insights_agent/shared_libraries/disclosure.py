"""Skill and Tool Disclosure — reusable introspection tool for all agents.

Provides agents with awareness of their own capabilities, available tools,
and the tools/skills of their sibling agents in the hierarchy.
"""

import logging
from google.adk.tools import ToolContext

logging.basicConfig(level=logging.INFO)


# Registry populated at import time by each agent module
_AGENT_REGISTRY: dict[str, dict] = {}


def register_agent(
    name: str,
    description: str,
    tools: list[str],
    skills: list[str] | None = None,
    state_keys_read: list[str] | None = None,
    state_keys_written: list[str] | None = None,
):
    """Register an agent's capabilities in the global disclosure registry.

    Call this at module level for each agent to populate the registry.

    Args:
        name: Agent name (e.g., "research_orchestrator")
        description: Brief description of the agent's role
        tools: List of tool function names available to this agent
        skills: Optional list of skill names (from SKILL.md)
        state_keys_read: Optional list of session state keys the agent reads
        state_keys_written: Optional list of session state keys the agent writes
    """
    _AGENT_REGISTRY[name] = {
        "name": name,
        "description": description,
        "tools": tools,
        "skills": skills or [],
        "state_keys_read": state_keys_read or [],
        "state_keys_written": state_keys_written or [],
    }


def disclose_capabilities(tool_context: ToolContext) -> dict:
    """Disclose the current agent's capabilities and available tools.

    Returns information about:
    - The calling agent's name and description
    - All tools available to the calling agent
    - Skills loaded by the calling agent
    - Session state keys the agent can read/write
    - A directory of all registered sibling agents and their capabilities

    Args:
        tool_context: The ADK tool context (provides agent name).

    Returns:
        dict with "self" (calling agent info) and "directory" (all agents).
    """
    # Try to identify the calling agent from the invocation context
    caller = "unknown"
    if hasattr(tool_context, '_invocation_context'):
        ctx = tool_context._invocation_context
        if hasattr(ctx, 'agent') and hasattr(ctx.agent, 'name'):
            caller = ctx.agent.name

    self_info = _AGENT_REGISTRY.get(caller, {
        "name": caller,
        "description": "No registration found for this agent.",
        "tools": [],
        "skills": [],
    })

    directory = {}
    for agent_name, info in _AGENT_REGISTRY.items():
        directory[agent_name] = {
            "description": info["description"],
            "tools": info["tools"],
            "skills": info["skills"],
        }

    return {
        "status": "ok",
        "self": self_info,
        "directory": directory,
        "total_agents_registered": len(_AGENT_REGISTRY),
    }


# Pre-register core agents
register_agent(
    name="root_agent",
    description="Orchestrator that delegates to specialized sub-agents for research, creative, AV, and evaluation.",
    tools=["preload_memory", "disclose_capabilities"],
    state_keys_read=["brand", "target_product", "target_audience", "key_selling_points", "autopilot_mode"],
    state_keys_written=[],
)

register_agent(
    name="research_orchestrator",
    description="Coordinates comprehensive market research pipeline: parallel research, merge, evaluate, enhance, compose report.",
    tools=["google_search", "recall_prior_insights", "save_draft_report_artifact"],
    state_keys_read=["target_search_trends", "target_yt_trends", "yt_video_analysis", "brand", "target_product"],
    state_keys_written=["combined_web_search_insights", "combined_final_cited_report", "sources"],
)

register_agent(
    name="ad_content_generator_agent",
    description="Generates ad copies, visual concepts, images (Gemini), and videos (Veo) with Gecko fidelity evaluation.",
    tools=[
        "save_select_ad_copy", "save_select_visual_concept",
        "generate_image", "generate_video",
        "save_img_artifact_key", "save_vid_artifact_key",
        "evaluate_media_fidelity",
    ],
    state_keys_read=["combined_final_cited_report", "target_search_trends", "target_yt_trends", "brand", "target_product"],
    state_keys_written=["final_select_ad_copies", "final_select_vis_concepts", "img_artifact_keys", "vid_artifact_keys"],
)

register_agent(
    name="av_editing_studio_agent",
    description="Produces commercials by compositing images/videos with Chirp voiceover, Lyria music, and Veo clips.",
    tools=[
        "generate_clips_parallel", "generate_voice_over", "generate_dialogue",
        "generate_branded_tagline", "mix_voice_with_audio",
        "generate_reference_image", "save_commercial_artifact",
    ],
    skills=["av-studio"],
    state_keys_read=["final_select_ad_copies", "final_select_vis_concepts", "commercial_duration"],
    state_keys_written=["commercial_artifact"],
)

register_agent(
    name="focus_group_evaluator_agent",
    description="Evaluates commercials with AI video analysis, simulated focus group panel, panelist portraits + testimonial videos, and final PDF report.",
    tools=[
        "analyze_commercial_video",
        "generate_panelist_portrait", "generate_panelist_testimonial",
        "save_creatives_and_research_report",
    ],
    skills=["focus-group"],
    state_keys_read=["commercial_artifact", "final_select_ad_copies", "final_select_vis_concepts", "combined_final_cited_report"],
    state_keys_written=["final_report_with_citations", "focus_group_panelists"],
)

register_agent(
    name="trends_and_insights_agent",
    description="Captures campaign metadata and helps user select Google Search and YouTube trends.",
    tools=["get_daily_gtrends", "get_youtube_trends", "save_search_trend", "save_youtube_trend"],
    state_keys_read=[],
    state_keys_written=["brand", "target_product", "target_audience", "key_selling_points", "target_search_trends", "target_yt_trends"],
)
