from google.genai import types
from google.adk.agents import Agent

from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from .tools import (
    generate_subject_image,
    generate_clip_with_frames,
    extract_frame_from_clip,
    concatenate_clips,
    trim_video,
    save_commercial_artifact,
)
from .music_tools import (
    generate_commercial_soundtrack,
    generate_sound_effects,
    combine_audio_with_video,
)
from .prompts import AV_STUDIO_INSTR

av_editing_studio_agent = Agent(
    model=config.worker_model,
    name="av_editing_studio_agent",
    description="Produces a 30-second commercial with professional soundtrack: generates SILENT Veo video clips, creates music with Lyria, and combines them for the final commercial.",
    instruction=AV_STUDIO_INSTR,
    tools=[
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
        # Final output
        save_commercial_artifact,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.6,  # Reduced from 1.0 for more accurate video planning
        top_p=0.9,
        top_k=40,
    ),
    before_model_callback=callbacks.rate_limit_callback,
)
