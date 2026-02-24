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
from .prompts import AV_STUDIO_INSTR

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
    ],
    generate_content_config=types.GenerateContentConfig(temperature=1.0),
    before_model_callback=callbacks.rate_limit_callback,
)
