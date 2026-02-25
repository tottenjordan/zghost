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
from .voice_tools import (
    generate_voice_over,
    generate_dialogue,
    generate_branded_tagline,
    mix_voice_with_audio,
)
from .recommendation_tools import recommend_audio_style
from .prompts import AV_STUDIO_INSTR

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
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.6,  # Reduced from 1.0 for more accurate video planning
        top_p=0.9,
        top_k=40,
    ),
    before_model_callback=callbacks.rate_limit_callback,
)
