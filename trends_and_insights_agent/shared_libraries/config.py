from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ResearchConfiguration:
    """Configuration for research-related models and parameters.

    Attributes:
        critic_model (str): Model for evaluation tasks.
        worker_model (str): Model for working/generation tasks.
        video_analysis_model (str): Model for video understanding.
        image_gen_model (str): Model for generating images.
        video_gen_model (str): Model for generating video.
        max_results_yt_trends (int): The value to set for `max_results` with the YouTube API
                                i.e., the number of video results to return.
        rate_limit_seconds (int): total duration to calculate the rate at which the agent queries the LLM API.
        rpm_quota (int): requests per minute threshold for agent LLM API rate limiter

    """

    critic_model: str = "gemini-3-flash-preview"
    worker_model: str = "gemini-3-flash-preview"
    video_analysis_model: str = "gemini-3-flash-preview"
    lite_planner_model: str = (
        "gemini-3-flash-preview"
    )
    image_gen_model: str = "imagen-4.0-ultra-generate-preview-06-06" # "imagen-4.0-fast-generate-preview-06-06"
    video_gen_model: str = (
        "veo-3.1-fast-generate-001"  # GA model | "veo-3.1-fast-generate-preview"
    )
    subject_image_gen_model: str = "gemini-3-pro-image-preview"

    max_results_yt_trends: int = 45

    # Adjust these values to limit the rate at which the agent queries the LLM API.
    rate_limit_seconds: int = 60
    rpm_quota: int = 1000


config = ResearchConfiguration()


@dataclass
class SetupConfiguration:
    """Configuration for general setup

    Attributes:
        state_init (str): a key indicating the state dict is initialized
        empty_session_state (dict): Empty dictionary with keys for initial ADK session state.

    """

    state_init = "_state_init"
    empty_session_state = {
        "state": {
            "final_select_ad_copies": {"final_select_ad_copies": []},
            "final_select_vis_concepts": {"final_select_vis_concepts": []},
            "img_artifact_keys": {"img_artifact_keys": []},
            "vid_artifact_keys": {"vid_artifact_keys": []},
            "brand": "",
            "target_product": "",
            "target_audience": "",
            "key_selling_points": "",
            "target_search_trends": {"target_search_trends": []},
            "target_yt_trends": {"target_yt_trends": []},
            # Template variables used in downstream agent instructions
            "yt_video_analysis": "",
            "combined_web_search_insights": "",
            "campaign_web_search_insights": "",
            "gs_web_search_insights": "",
            "yt_web_search_insights": "",
            "combined_final_cited_report": "",
            "sources": {},
            "final_report_with_citations": "",
            "commercial_artifact": "",
        }
    }


setup_config = SetupConfiguration()


@dataclass
class AudioConfiguration:
    """Configuration for audio generation (Chirp voice & Lyria music).

    Provides presets and samples for different campaign styles, making it easier
    to select appropriate voice and music combinations.
    """

    # Chirp voice model
    chirp_model: str = "models/chirp-3-hd"  # Latest Chirp 3 HD model

    # Lyria music model
    lyria_model: str = "models/music-lyria-1"

    # Quick access to popular voice/music combinations
    quick_styles: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize quick style combinations."""
        self.quick_styles = {
            "tech_modern": {
                "voice": {
                    "style": "professional_male",
                    "rate": 0.95,
                    "pitch": -1.0,
                    "description": "Authoritative tech narrator"
                },
                "music": {
                    "genre": "electronic/ambient",
                    "mood": "innovative",
                    "tempo": "120-128 BPM",
                    "instruments": "synths, digital drums"
                }
            },
            "lifestyle_warm": {
                "voice": {
                    "style": "warm_female",
                    "rate": 1.0,
                    "pitch": 0.5,
                    "description": "Friendly, relatable narrator"
                },
                "music": {
                    "genre": "indie pop",
                    "mood": "upbeat, optimistic",
                    "tempo": "110-120 BPM",
                    "instruments": "acoustic guitar, light percussion"
                }
            },
            "youth_energy": {
                "voice": {
                    "style": "energetic_male",
                    "rate": 1.15,
                    "pitch": 2.0,
                    "description": "Young, dynamic voice"
                },
                "music": {
                    "genre": "hip hop/trap",
                    "mood": "energetic, confident",
                    "tempo": "140-160 BPM",
                    "instruments": "808 drums, trap hi-hats"
                }
            },
            "luxury_premium": {
                "voice": {
                    "style": "british_female",
                    "rate": 0.9,
                    "pitch": -0.5,
                    "description": "Sophisticated, refined narrator"
                },
                "music": {
                    "genre": "orchestral/minimal",
                    "mood": "elegant, sophisticated",
                    "tempo": "80-100 BPM",
                    "instruments": "strings, piano"
                }
            },
            "family_friendly": {
                "voice": {
                    "style": "warm_female",
                    "rate": 0.95,
                    "pitch": 0,
                    "description": "Nurturing, clear for all ages"
                },
                "music": {
                    "genre": "acoustic/folk",
                    "mood": "warm, cheerful",
                    "tempo": "100-110 BPM",
                    "instruments": "ukulele, light drums, bells"
                }
            }
        }


audio_config = AudioConfiguration()


# Import the detailed audio presets
try:
    from .audio_config import (
        VOICE_PRESETS,
        MUSIC_PRESETS,
        CAMPAIGN_STYLES,
        get_voice_preset,
        get_music_preset,
        get_campaign_style
    )

    # Extend AudioConfiguration with detailed presets
    audio_config.voice_presets = VOICE_PRESETS
    audio_config.music_presets = MUSIC_PRESETS
    audio_config.campaign_styles = CAMPAIGN_STYLES
    audio_config.get_voice_preset = get_voice_preset
    audio_config.get_music_preset = get_music_preset
    audio_config.get_campaign_style = get_campaign_style
except ImportError:
    # Fallback if detailed config not available
    pass
