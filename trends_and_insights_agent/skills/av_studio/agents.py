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
from .music_tools import (
    generate_commercial_soundtrack,
    generate_sound_effects,
    combine_audio_with_video,
)
from .voice_tools import (
    generate_voice_over,
    generate_dialogue,
    generate_branded_tagline,
    mix_voice_with_audio,
)
from .recommendation_tools import recommend_audio_style
from .prompts import AV_STUDIO_INSTR

# Load this skill's own SKILL.md for self-contained documentation
_skill_dir = pathlib.Path(__file__).parent
_skill = load_skill_from_dir(_skill_dir)
_skill_toolset = SkillToolset(skills=[_skill])

av_editing_studio_agent = Agent(
    model=config.worker_model,
    name="av_editing_studio_agent",
    description="Produces a 30-second commercial with professional audio: SILENT Veo video, Lyria music, and Chirp voice-over combined for broadcast-quality output.",
    instruction=AV_STUDIO_INSTR,
    tools=[
        # Audio recommendations
        recommend_audio_style,
        # Video generation (silent)
        generate_subject_image,
        generate_clip_with_frames,
        extract_frame_from_clip,
        concatenate_clips,
        trim_video,
        # Music generation (Lyria)
        generate_commercial_soundtrack,
        generate_sound_effects,
        combine_audio_with_video,
        # Voice generation (Chirp)
        generate_voice_over,
        generate_dialogue,
        generate_branded_tagline,
        mix_voice_with_audio,
        # Final output
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
