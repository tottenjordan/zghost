import pathlib

from google.genai import types
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools.skill_toolset import SkillToolset

from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from ...skills.skill_loader import load_skill_from_dir
from .tools import (
    generate_subject_image,
    generate_clip_with_frames,
    extract_frame_from_clip,
    concatenate_clips,
    trim_video,
    save_commercial_artifact,
    validate_character_consistency,
)
from .prompts import AV_STUDIO_INSTR

# Load this skill's own SKILL.md for self-contained documentation
_skill_dir = pathlib.Path(__file__).parent
_skill = load_skill_from_dir(_skill_dir)
_skill_toolset = SkillToolset(skills=[_skill])

av_editing_studio_agent = Agent(
    model=config.worker_model,
    name="av_editing_studio_agent",
    description="Produces a 30-second commercial by generating subject reference images, chaining Veo clips with first/last frame matching, and assembling with ffmpeg.",
    instruction=AV_STUDIO_INSTR,
    tools=[
        generate_subject_image,
        generate_clip_with_frames,
        extract_frame_from_clip,
        concatenate_clips,
        trim_video,
        save_commercial_artifact,
        validate_character_consistency,
        _skill_toolset,
    ],
    generate_content_config=types.GenerateContentConfig(temperature=1.0),
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_level="MEDIUM")
    ),
    before_model_callback=callbacks.rate_limit_callback,
)
