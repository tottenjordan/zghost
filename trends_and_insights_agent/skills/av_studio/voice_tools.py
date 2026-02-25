"""Voice-over generation tools using Google's Chirp 3 HD for commercial narration."""

import os
import logging
import uuid
import json
from typing import Optional, Dict, List, Any
from google.cloud import texttospeech_v1beta1 as texttospeech
from google.adk.tools import ToolContext
from ...shared_libraries.config import config, audio_config
from ...shared_libraries.utils import upload_blob_to_gcs
try:
    from ...shared_libraries.audio_config import VOICE_PRESETS as DETAILED_VOICE_PRESETS
except ImportError:
    DETAILED_VOICE_PRESETS = None

logging.basicConfig(level=logging.INFO)

# Get GCS bucket at runtime (Agent Engine injects env vars after import)
def get_gcs_bucket():
    bucket = os.environ.get("BUCKET")
    if not bucket:
        raise Exception("BUCKET environment variable not set")
    return bucket

# Initialize Text-to-Speech client
tts_client = texttospeech.TextToSpeechClient()


# Chirp voice configurations for different commercial styles
CHIRP_VOICES = {
    "professional_male": {
        "language_code": "en-US",
        "name": "en-US-Chirp-M",  # Male voice
        "description": "Professional, confident male narrator"
    },
    "professional_female": {
        "language_code": "en-US",
        "name": "en-US-Chirp-F",  # Female voice
        "description": "Professional, warm female narrator"
    },
    "energetic_male": {
        "language_code": "en-US",
        "name": "en-US-Chirp-M",
        "description": "Upbeat, energetic male voice for youth-oriented ads"
    },
    "warm_female": {
        "language_code": "en-US",
        "name": "en-US-Chirp-F",
        "description": "Warm, friendly female voice for lifestyle brands"
    },
    "british_male": {
        "language_code": "en-GB",
        "name": "en-GB-Chirp-M",
        "description": "Sophisticated British male accent"
    },
    "british_female": {
        "language_code": "en-GB",
        "name": "en-GB-Chirp-F",
        "description": "Sophisticated British female accent"
    },
}


def generate_voice_over(
    script: str,
    voice_style: str,
    speaking_rate: float,
    pitch: float,
    timing_marks: List[Dict[str, Any]],
    tool_context: ToolContext,
) -> dict:
    """Generates professional voice-over narration using Google's Chirp 3 HD model.

    Creates high-quality voice narration for commercials with precise control
    over voice characteristics, pacing, and emotional delivery.

    Args:
        script (str): The narration script with optional SSML markup for emphasis,
            pauses, and pronunciation. Supports <break>, <emphasis>, <prosody> tags.
        voice_style (str): Voice preset from CHIRP_VOICES (e.g., "professional_male",
            "warm_female", "energetic_male", "british_female").
        speaking_rate (float): Speed of speech (0.5-2.0, where 1.0 is normal).
            Use 0.9 for clear product names, 1.1 for energetic delivery.
        pitch (float): Voice pitch adjustment (-10.0 to +10.0 semitones, 0 is default).
            Positive values for brighter tone, negative for deeper.
        timing_marks (list): List of timing cues for synchronization.
            Format: [{"text": "product name", "timestamp": 15.5}, ...]
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and voice-over details. Keys: "status", "gcs_uri", "local_path",
            "duration_seconds", "word_timings".
    """
    try:
        # Get voice configuration
        if voice_style not in CHIRP_VOICES:
            return {
                "status": "failed",
                "error": f"Unknown voice style: {voice_style}. Choose from: {list(CHIRP_VOICES.keys())}"
            }

        voice_config = CHIRP_VOICES[voice_style]

        # Prepare SSML script with timing marks
        ssml_script = f"""<speak>
            <prosody rate="{speaking_rate}" pitch="{pitch:+.1f}st">
                {script}
            </prosody>
        </speak>"""

        # Configure voice parameters
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config["language_code"],
            name=voice_config["name"],
        )

        # Configure audio output - Chirp 3 HD settings
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            sample_rate_hertz=48000,  # High-quality audio
            # Enable time point info for word-level timing
            enable_time_pointing=[
                texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK
            ] if timing_marks else None
        )

        # Prepare synthesis input
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_script)

        # Generate voice-over
        request = texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
            enable_time_pointing=True  # Get word timings
        )

        response = tts_client.synthesize_speech(request=request)

        # Extract audio content
        audio_content = response.audio_content

        # Save voice-over locally
        safe_style = voice_style.replace(" ", "_")
        filename = f"voiceover_{safe_style}_{str(uuid.uuid4())[:8]}.mp3"
        local_dir = "session_media/av_studio/voiceover"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        with open(local_path, "wb") as f:
            f.write(audio_content)

        # Calculate duration (approximate from file size and bitrate)
        file_size = len(audio_content)
        bitrate = 128000  # 128 kbps for MP3
        duration_seconds = (file_size * 8) / bitrate

        # Upload to GCS
        gcs_folder = tool_context.state.get("gcs_folder", "default")
        destination_blob = f"{gcs_folder}/av_studio/voiceover/{filename}"
        upload_blob_to_gcs(
            source_file_name=local_path,
            destination_blob_name=destination_blob,
        )

        bucket_name = get_gcs_bucket().replace("gs://", "")
        gcs_uri = f"gs://{bucket_name}/{destination_blob}"

        # Extract word timings if available
        word_timings = []
        if hasattr(response, 'timepoints') and response.timepoints:
            for timepoint in response.timepoints:
                word_timings.append({
                    "mark_name": timepoint.mark_name,
                    "time_seconds": timepoint.time_seconds
                })

        logging.info(f"Generated voice-over with {voice_style} at {gcs_uri}")

        return {
            "status": "ok",
            "gcs_uri": gcs_uri,
            "local_path": local_path,
            "voice_style": voice_style,
            "duration_seconds": duration_seconds,
            "word_timings": word_timings,
            "metadata": {
                "speaking_rate": speaking_rate,
                "pitch": pitch,
                "voice_config": voice_config,
            }
        }

    except Exception as e:
        logging.error(f"Error generating voice-over: {e}")
        return {"status": "failed", "error": str(e)}


def generate_dialogue(
    dialogue_lines: List[Dict[str, str]],
    scene_context: str,
    tool_context: ToolContext,
) -> dict:
    """Generates character dialogue for commercials using different Chirp voices.

    Creates natural-sounding conversations between characters with distinct
    voices and appropriate emotional delivery.

    Args:
        dialogue_lines (list): List of dialogue entries.
            Format: [
                {"character": "Customer", "line": "Is this really that easy?",
                 "emotion": "curious", "voice": "warm_female"},
                {"character": "Expert", "line": "Absolutely! Let me show you.",
                 "emotion": "confident", "voice": "professional_male"}
            ]
        scene_context (str): Description of the scene and interaction context.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and dialogue audio files with timing information.
    """
    try:
        generated_dialogue = []

        for i, entry in enumerate(dialogue_lines):
            character = entry.get("character", f"Character_{i}")
            line = entry["line"]
            emotion = entry.get("emotion", "neutral")
            voice_style = entry.get("voice", "professional_male")

            # Adjust prosody based on emotion
            emotion_prosody = {
                "excited": {"rate": 1.15, "pitch": 2.0, "volume": "+2dB"},
                "curious": {"rate": 1.0, "pitch": 1.0, "volume": "0dB"},
                "confident": {"rate": 0.95, "pitch": -1.0, "volume": "+1dB"},
                "warm": {"rate": 0.95, "pitch": 0.5, "volume": "0dB"},
                "surprised": {"rate": 1.1, "pitch": 3.0, "volume": "+1dB"},
                "calm": {"rate": 0.9, "pitch": -0.5, "volume": "-1dB"},
                "neutral": {"rate": 1.0, "pitch": 0, "volume": "0dB"},
            }.get(emotion, {"rate": 1.0, "pitch": 0, "volume": "0dB"})

            # Generate SSML with emotion-appropriate prosody
            ssml = f"""<speak>
                <prosody rate="{emotion_prosody['rate']}"
                         pitch="{emotion_prosody['pitch']:+.1f}st"
                         volume="{emotion_prosody['volume']}">
                    {line}
                </prosody>
            </speak>"""

            # Get voice configuration
            voice_config = CHIRP_VOICES.get(voice_style, CHIRP_VOICES["professional_male"])

            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_config["language_code"],
                name=voice_config["name"],
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                sample_rate_hertz=48000,
            )

            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

            response = tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Save dialogue line
            safe_character = character.replace(" ", "_").lower()
            filename = f"dialogue_{safe_character}_{i}_{str(uuid.uuid4())[:8]}.mp3"
            local_dir = "session_media/av_studio/dialogue"
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, filename)

            with open(local_path, "wb") as f:
                f.write(response.audio_content)

            # Upload to GCS
            gcs_folder = tool_context.state.get("gcs_folder", "default")
            destination_blob = f"{gcs_folder}/av_studio/dialogue/{filename}"
            upload_blob_to_gcs(
                source_file_name=local_path,
                destination_blob_name=destination_blob,
            )

            bucket_name = get_gcs_bucket().replace("gs://", "")
            gcs_uri = f"gs://{bucket_name}/{destination_blob}"

            # Calculate approximate duration
            file_size = len(response.audio_content)
            duration_seconds = (file_size * 8) / 128000  # 128 kbps

            generated_dialogue.append({
                "character": character,
                "line": line,
                "emotion": emotion,
                "voice_style": voice_style,
                "gcs_uri": gcs_uri,
                "local_path": local_path,
                "duration_seconds": duration_seconds,
                "sequence": i,
            })

            logging.info(f"Generated dialogue for {character} at {gcs_uri}")

        return {
            "status": "ok",
            "dialogue": generated_dialogue,
            "total_lines": len(generated_dialogue),
            "scene_context": scene_context,
        }

    except Exception as e:
        logging.error(f"Error generating dialogue: {e}")
        return {"status": "failed", "error": str(e)}


def generate_branded_tagline(
    tagline: str,
    brand_voice: str,
    emphasis_words: List[str],
    tool_context: ToolContext,
) -> dict:
    """Generates the brand tagline or slogan with specific emphasis and delivery.

    Creates the final branded message with perfect delivery for maximum impact,
    typically used at the end of commercials.

    Args:
        tagline (str): The brand tagline or slogan (e.g., "Just Do It",
            "Think Different", "Because You're Worth It").
        brand_voice (str): Voice style that matches brand identity from CHIRP_VOICES.
        emphasis_words (list): Words to emphasize in the tagline for impact.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and tagline audio with optimal delivery.
    """
    try:
        # Build SSML with emphasis on key words
        ssml_parts = []
        words = tagline.split()

        for word in words:
            # Remove punctuation for comparison
            clean_word = word.strip(".,!?").lower()
            if clean_word in [e.lower() for e in emphasis_words]:
                # Emphasize this word
                ssml_parts.append(f'<emphasis level="strong">{word}</emphasis>')
            else:
                ssml_parts.append(word)

        emphasized_tagline = " ".join(ssml_parts)

        # Create SSML with brand-appropriate delivery
        ssml_script = f"""<speak>
            <break time="200ms"/>
            <prosody rate="0.9" pitch="-1.0st">
                {emphasized_tagline}
            </prosody>
            <break time="500ms"/>
        </speak>"""

        # Get voice configuration
        voice_config = CHIRP_VOICES.get(brand_voice, CHIRP_VOICES["professional_male"])

        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config["language_code"],
            name=voice_config["name"],
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            sample_rate_hertz=48000,
            effects_profile_id=["large-home-entertainment-class-device"],  # Enhanced audio
        )

        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_script)

        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Save tagline audio
        filename = f"tagline_{str(uuid.uuid4())[:8]}.mp3"
        local_dir = "session_media/av_studio/tagline"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        with open(local_path, "wb") as f:
            f.write(response.audio_content)

        # Upload to GCS
        gcs_folder = tool_context.state.get("gcs_folder", "default")
        destination_blob = f"{gcs_folder}/av_studio/tagline/{filename}"
        upload_blob_to_gcs(
            source_file_name=local_path,
            destination_blob_name=destination_blob,
        )

        bucket_name = get_gcs_bucket().replace("gs://", "")
        gcs_uri = f"gs://{bucket_name}/{destination_blob}"

        logging.info(f"Generated brand tagline at {gcs_uri}")

        return {
            "status": "ok",
            "gcs_uri": gcs_uri,
            "local_path": local_path,
            "tagline": tagline,
            "brand_voice": brand_voice,
            "emphasis_words": emphasis_words,
        }

    except Exception as e:
        logging.error(f"Error generating tagline: {e}")
        return {"status": "failed", "error": str(e)}


def mix_voice_with_audio(
    video_gcs_uri: str,
    music_gcs_uri: str,
    voice_config: Dict[str, Any],
    output_name: str,
    tool_context: ToolContext,
) -> dict:
    """Professionally mixes voice-over, music, and SFX with the video.

    Creates the final commercial with balanced audio levels, ducking music
    during voice-over, and proper stereo mixing.

    Args:
        video_gcs_uri (str): GCS URI of the silent video.
        music_gcs_uri (str): GCS URI of the background music.
        voice_config (dict): Voice-over configuration.
            Format: {
                "voiceover_uri": "gs://...",
                "dialogue": [{"uri": "...", "timestamp": 5.0}, ...],
                "tagline_uri": "gs://...",
                "tagline_timestamp": 28.0
            }
        output_name (str): Name for the final output.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and final mixed video with professional audio.
    """
    try:
        import subprocess
        import tempfile
        from ...shared_libraries.utils import download_blob
        from google.cloud import storage

        storage_client = storage.Client()
        bucket_name = get_gcs_bucket().replace("gs://", "")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Download all media files
            video_blob = video_gcs_uri.replace(f"gs://{bucket_name}/", "")
            music_blob = music_gcs_uri.replace(f"gs://{bucket_name}/", "")

            video_bytes = download_blob(bucket_name, video_blob)
            music_bytes = download_blob(bucket_name, music_blob)

            video_path = os.path.join(tmp_dir, "video.mp4")
            music_path = os.path.join(tmp_dir, "music.mp3")

            with open(video_path, "wb") as f:
                f.write(video_bytes)
            with open(music_path, "wb") as f:
                f.write(music_bytes)

            # Build complex audio filter for professional mixing
            inputs = ["-i", video_path, "-i", music_path]

            # Start with music at reduced volume for ducking
            filter_complex = "[1:a]volume=0.3[music_low]"

            # Add voice-over if present
            if voice_config.get("voiceover_uri"):
                vo_blob = voice_config["voiceover_uri"].replace(f"gs://{bucket_name}/", "")
                vo_bytes = download_blob(bucket_name, vo_blob)
                vo_path = os.path.join(tmp_dir, "voiceover.mp3")
                with open(vo_path, "wb") as f:
                    f.write(vo_bytes)
                inputs.extend(["-i", vo_path])

                # Apply compression and EQ to voice for broadcast quality
                filter_complex += ";[2:a]highpass=f=80,lowpass=f=12000,compand=attacks=0:points=-30/-900|-20/-20|0/0|20/20[vo_clean]"

            # Add dialogue lines with timing
            dialogue_inputs = []
            if voice_config.get("dialogue"):
                for i, dialogue in enumerate(voice_config["dialogue"]):
                    d_blob = dialogue["uri"].replace(f"gs://{bucket_name}/", "")
                    d_bytes = download_blob(bucket_name, d_blob)
                    d_path = os.path.join(tmp_dir, f"dialogue_{i}.mp3")
                    with open(d_path, "wb") as f:
                        f.write(d_bytes)
                    inputs.extend(["-i", d_path])

                    # Add delay for proper timing
                    timestamp_ms = int(dialogue["timestamp"] * 1000)
                    filter_complex += f";[{3+i}:a]adelay={timestamp_ms}|{timestamp_ms}[dialogue_{i}]"
                    dialogue_inputs.append(f"[dialogue_{i}]")

            # Add tagline with impact
            if voice_config.get("tagline_uri"):
                tag_blob = voice_config["tagline_uri"].replace(f"gs://{bucket_name}/", "")
                tag_bytes = download_blob(bucket_name, tag_blob)
                tag_path = os.path.join(tmp_dir, "tagline.mp3")
                with open(tag_path, "wb") as f:
                    f.write(tag_bytes)
                last_input_idx = len(inputs) // 2
                inputs.extend(["-i", tag_path])

                # Add reverb and delay for tagline impact
                timestamp_ms = int(voice_config.get("tagline_timestamp", 28) * 1000)
                filter_complex += f";[{last_input_idx}:a]adelay={timestamp_ms}|{timestamp_ms},aecho=0.8:0.88:60:0.4[tagline]"

            # Create sidechain compression for automatic ducking
            mix_inputs = "[music_low]"
            if voice_config.get("voiceover_uri"):
                mix_inputs += "[vo_clean]"
            mix_inputs += "".join(dialogue_inputs)
            if voice_config.get("tagline_uri"):
                mix_inputs += "[tagline]"

            # Final mix with dynamic range compression
            num_inputs = mix_inputs.count("[")
            filter_complex += f";{mix_inputs}amix=inputs={num_inputs}:duration=first,dynaudnorm=p=0.95:m=10:s=5[final_audio]"

            # Build ffmpeg command
            cmd = ["ffmpeg"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[final_audio]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",  # High-quality audio
                "-ar", "48000",   # Professional sample rate
                "-ac", "2",       # Stereo
                "-shortest",
                os.path.join(tmp_dir, f"{output_name}.mp4")
            ]

            # Execute ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {"status": "failed", "error": f"ffmpeg error: {result.stderr}"}

            # Save and upload final video
            output_path = os.path.join(tmp_dir, f"{output_name}.mp4")
            with open(output_path, "rb") as f:
                output_bytes = f.read()

            local_dir = "session_media/av_studio/final"
            os.makedirs(local_dir, exist_ok=True)
            local_final = os.path.join(local_dir, f"{output_name}.mp4")
            with open(local_final, "wb") as f:
                f.write(output_bytes)

            # Upload to GCS
            gcs_folder = tool_context.state.get("gcs_folder", "default")
            destination_blob = f"{gcs_folder}/av_studio/final/{output_name}.mp4"

            bucket = storage_client.get_bucket(bucket_name)
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(local_final)

            final_gcs_uri = f"gs://{bucket_name}/{destination_blob}"

            logging.info(f"Created final commercial with professional audio mix at {final_gcs_uri}")

            return {
                "status": "ok",
                "gcs_uri": final_gcs_uri,
                "local_path": local_final,
                "has_music": True,
                "has_voiceover": bool(voice_config.get("voiceover_uri")),
                "has_dialogue": bool(voice_config.get("dialogue")),
                "has_tagline": bool(voice_config.get("tagline_uri")),
            }

    except Exception as e:
        logging.error(f"Error mixing voice with audio: {e}")
        return {"status": "failed", "error": str(e)}