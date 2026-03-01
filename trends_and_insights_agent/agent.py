import os
import pathlib
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import preload_memory
from google.adk.tools.skill_toolset import SkillToolset

from .skills.trend_discovery.agents import trends_and_insights_agent
from .skills.market_research.agents import research_orchestrator
from .skills.ad_creative.agents import ad_content_generator_agent
from .skills.ad_creative.tools import save_creatives_and_research_report
from .skills.av_studio.agents import av_editing_studio_agent
from .skills.focus_group.agents import focus_group_evaluator_agent
from .skills.skill_loader import load_all_skills

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import (
    GLOBAL_INSTR,
    ROOT_AGENT_INSTR,
)
from google.adk.planners import BuiltInPlanner

# Load all skills for dynamic discovery
_skills_dir = pathlib.Path(__file__).parent / "skills"
_skills = load_all_skills(_skills_dir)
_skill_toolset = SkillToolset(skills=_skills)

root_agent = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant using the services of multiple sub-agents.",
    instruction=ROOT_AGENT_INSTR,
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        research_orchestrator,
        trends_and_insights_agent,
        ad_content_generator_agent,
        av_editing_studio_agent,
        focus_group_evaluator_agent,
    ],
    tools=[save_creatives_and_research_report, preload_memory, _skill_toolset],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks._load_session_state,
        callbacks.campaign_callback_function,
    ],
    before_model_callback=callbacks.rate_limit_callback,
    after_agent_callback=callbacks.save_session_to_memory_callback,
)
