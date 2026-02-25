"""Audio recommendation tools for the AV studio agent."""

from google.adk.tools import ToolContext
from .audio_selector import get_audio_recommendations


def recommend_audio_style(tool_context: ToolContext) -> dict:
    """Analyzes campaign context and recommends optimal voice and music styles.

    This tool examines the brand, target audience, trends, and ad copy to suggest
    the most effective audio combination for the commercial. It provides specific
    voice presets, music genres, and mixing strategies.

    Args:
        tool_context (ToolContext): The tool context with campaign data.

    Returns:
        dict: Comprehensive audio recommendations including:
            - Voice preset with speaking rate and pitch
            - Music genre, mood, and instruments
            - Mixing strategy and levels
            - Suggested sound effects with timing
            - Script writing style guide
            - Quick preset options
    """
    try:
        recommendations = get_audio_recommendations(tool_context)

        # Format for easy consumption by the agent
        formatted = {
            "status": "ok",
            "voice_recommendation": {
                "preset_name": recommendations["audio_style"]["voice_recommendation"]["preset"].name,
                "description": recommendations["audio_style"]["voice_recommendation"]["preset"].description,
                "speaking_rate": recommendations["audio_style"]["voice_recommendation"]["speaking_rate"],
                "pitch": recommendations["audio_style"]["voice_recommendation"]["pitch"],
                "voice_id": recommendations["audio_style"]["voice_recommendation"]["preset"].voice_id,
                "reasoning": recommendations["audio_style"]["voice_recommendation"]["reasoning"],
            },
            "music_recommendation": {
                "genre": recommendations["audio_style"]["music_recommendation"]["genre"],
                "mood": recommendations["audio_style"]["music_recommendation"]["mood"],
                "tempo": recommendations["audio_style"]["music_recommendation"]["tempo"],
                "instruments": recommendations["audio_style"]["music_recommendation"]["instruments"],
                "energy_curve": recommendations["audio_style"]["music_recommendation"]["preset"].energy_curve,
                "reasoning": recommendations["audio_style"]["music_recommendation"]["reasoning"],
            },
            "mixing_strategy": recommendations["audio_style"]["mixing_strategy"],
            "suggested_sfx": recommendations["audio_style"]["suggested_sfx"],
            "script_style_guide": recommendations["script_style"],
            "quick_options": recommendations["quick_presets"],
            "campaign_analysis": {
                "audience": recommendations["audio_style"]["campaign_context"]["audience_profile"],
                "brand_personality": recommendations["audio_style"]["campaign_context"]["brand_personality"],
                "energy_level": recommendations["audio_style"]["campaign_context"]["energy_level"],
                "trend_context": recommendations["audio_style"]["campaign_context"]["trend_context"],
            }
        }

        # Add usage instructions
        formatted["usage_notes"] = """
Based on your campaign analysis, here are the recommended settings:

VOICE OVER:
- Use voice style: {voice}
- Set speaking_rate to {rate}
- Set pitch to {pitch}
- Focus on: {voice_focus}

MUSIC:
- Genre: {genre}
- Create a {mood} mood
- Use these instruments: {instruments}
- Follow this energy curve: {energy}

MIXING:
- Set voice level to {voice_db}dB
- Set music to {music_db}dB (ducking to {duck_db}dB during voice)
- Add suggested SFX at marked timings

You can also choose from the quick_options for simpler selection.
""".format(
            voice=formatted["voice_recommendation"]["preset_name"],
            rate=formatted["voice_recommendation"]["speaking_rate"],
            pitch=formatted["voice_recommendation"]["pitch"],
            voice_focus=formatted["voice_recommendation"]["description"],
            genre=formatted["music_recommendation"]["genre"],
            mood=formatted["music_recommendation"]["mood"],
            instruments=formatted["music_recommendation"]["instruments"],
            energy=formatted["music_recommendation"]["energy_curve"],
            voice_db=formatted["mixing_strategy"]["voice_level_db"],
            music_db=formatted["mixing_strategy"]["music_level_db"],
            duck_db=formatted["mixing_strategy"]["music_level_db"] - formatted["mixing_strategy"]["ducking_amount_db"],
        )

        return formatted

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "fallback": {
                "voice": "professional_female",
                "music": "indie pop upbeat",
                "mixing": "voice_focused"
            }
        }