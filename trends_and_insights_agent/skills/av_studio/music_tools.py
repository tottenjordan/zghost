"""Music generation tools using Google's Lyria 2 model for commercial soundtracks."""

import os
import logging
import uuid
import time
import base64
from typing import Optional, Dict, Any, List
from google.adk.tools import ToolContext
from ...shared_libraries.config import audio_config as config
from ...shared_libraries.utils import upload_blob_to_gcs

logging.basicConfig(level=logging.INFO)


def _retry_with_backoff(fn, max_attempts=3, base_delay=5):
    """Retry a function with exponential backoff.

    Args:
        fn: Callable to retry (should take no arguments)
        max_attempts: Maximum number of attempts (default 3)
        base_delay: Base delay in seconds (default 5)

    Returns:
        The result of fn() if successful

    Raises:
        The last exception if all attempts fail
    """
    last_exception = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logging.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logging.error(
                    f"All {max_attempts} attempts failed. Last error: {e}"
                )
    raise last_exception

# Get GCS bucket at runtime (Agent Engine injects env vars after import)
def get_gcs_bucket():
    bucket = os.environ.get("BUCKET")
    if not bucket:
        raise Exception("BUCKET environment variable not set")
    return bucket

GCS_BUCKET = None  # Will be evaluated at runtime


def _call_lyria_predict(prompt: str, negative_prompt: str = "", sample_count: int = 1, seed: int | None = None) -> List[bytes]:
    """Call Lyria 2 via Vertex AI predict endpoint. Returns list of WAV bytes."""
    import google.auth
    import google.auth.transport.requests
    import requests

    credentials, _ = google.auth.default()
    credentials.refresh(google.auth.transport.requests.Request())

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{config.lyria_model}:predict"

    payload: Dict[str, Any] = {"instances": [{"prompt": prompt}], "parameters": {}}
    if negative_prompt:
        payload["parameters"]["negative_prompt"] = negative_prompt
    if seed is not None:
        payload["parameters"]["seed"] = seed
    elif sample_count > 1:
        payload["parameters"]["sample_count"] = sample_count
    # Cannot set both seed and sample_count per Lyria docs

    headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}
    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()
    return [base64.b64decode(pred["bytesBase64Encoded"]) for pred in result.get("predictions", [])]


def generate_commercial_soundtrack(
    prompt: str,
    duration_seconds: int,
    genre: str,
    mood: str,
    instruments: str,
    tool_context: ToolContext,
) -> dict:
    """Generates a commercial soundtrack using Google's Lyria 2 music generation model.

    This tool creates background music for commercials that matches the brand,
    target audience, and emotional tone of the campaign. Music is generated
    separately from video to ensure full control over audio quality.
    Lyria 2 produces 30-second WAV clips at 48kHz.

    Args:
        prompt (str): Detailed description of the desired music, including style,
            tempo, progression, and how it should support the commercial narrative.
        duration_seconds (int): Length of the soundtrack (typically 30 for commercials).
            Note: Lyria 2 always generates ~30s clips.
        genre (str): Musical genre (e.g., "upbeat pop", "corporate ambient",
            "indie folk", "electronic", "orchestral").
        mood (str): Emotional tone (e.g., "inspirational", "energetic", "calm",
            "playful", "sophisticated").
        instruments (str): Key instruments to feature (e.g., "acoustic guitar and piano",
            "synth pads", "full orchestra", "minimal percussion").
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and paths. Keys: "status", "gcs_uri", "local_path", "metadata".
    """
    try:
        brand = tool_context.state.get('brand', 'general')
        target_audience = tool_context.state.get('target_audience', 'general')

        full_prompt = (
            f"{genre} soundtrack, {mood} mood, featuring {instruments}. "
            f"Brand: {brand}, audience: {target_audience}. "
            f"{prompt}"
        )
        negative_prompt = "vocals, lyrics, singing, speech, voice"

        start_time = time.time()
        wav_list = _retry_with_backoff(
            lambda: _call_lyria_predict(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
            ),
            max_attempts=3,
            base_delay=5,
        )
        elapsed_time = time.time() - start_time

        if not wav_list:
            return {"status": "failed", "error": "No music generated from Lyria 2"}

        audio_bytes = wav_list[0]

        if len(audio_bytes) < 1000:
            logging.warning(
                f"Generated audio suspiciously small: {len(audio_bytes)} bytes."
            )
            return {
                "status": "failed",
                "error": f"Generated audio too small: {len(audio_bytes)} bytes",
            }

        logging.info(
            f"Music generation succeeded - Model: {config.lyria_model}, "
            f"Prompt length: {len(full_prompt)} chars, "
            f"Response size: {len(audio_bytes)} bytes, "
            f"Elapsed: {elapsed_time:.2f}s"
        )

        filename = f"soundtrack_{genre.replace(' ', '_')}_{str(uuid.uuid4())[:8]}.wav"
        local_dir = "session_media/av_studio/music"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        with open(local_path, "wb") as f:
            f.write(audio_bytes)

        gcs_folder = tool_context.state.get("gcs_folder", "default")
        destination_blob = f"{gcs_folder}/av_studio/music/{filename}"
        upload_blob_to_gcs(
            source_file_name=local_path,
            destination_blob_name=destination_blob,
        )

        bucket_name = get_gcs_bucket().replace("gs://", "")
        gcs_uri = f"gs://{bucket_name}/{destination_blob}"

        logging.info(f"Generated soundtrack at {gcs_uri}")

        return {
            "status": "ok",
            "gcs_uri": gcs_uri,
            "local_path": local_path,
            "metadata": {
                "genre": genre,
                "mood": mood,
                "instruments": instruments,
                "duration": duration_seconds,
            },
        }

    except Exception as e:
        logging.error(f"Error generating soundtrack: {e}")
        return {"status": "failed", "error": str(e)}


def generate_sound_effects(
    effects_list: list,
    timing_cues: str,
    tool_context: ToolContext,
) -> dict:
    """Generates specific sound effects for the commercial using Lyria 2.

    Creates individual sound effects that can be layered over the video
    at specific moments (e.g., product reveal, transition swooshes, button clicks).

    Args:
        effects_list (list): List of sound effects needed (e.g.,
            ["swoosh transition", "product sparkle", "button click", "success chime"]).
        timing_cues (str): Description of when each effect should occur in the video.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and list of generated effects with their GCS URIs.
    """
    try:
        generated_effects = []
        brand = tool_context.state.get('brand', 'modern')

        for effect_name in effects_list:
            prompt = (
                f"Short sound effect: {effect_name}. "
                f"Professional, commercial-quality. Context: {timing_cues}. "
                f"Brand tone: {brand}"
            )

            try:
                wav_list = _call_lyria_predict(
                    prompt=prompt,
                    negative_prompt="vocals, lyrics, singing, speech",
                )
            except Exception as e:
                logging.warning(f"Failed to generate SFX '{effect_name}': {e}")
                continue

            if wav_list:
                audio_bytes = wav_list[0]

                safe_name = effect_name.replace(" ", "_").lower()
                filename = f"sfx_{safe_name}_{str(uuid.uuid4())[:8]}.wav"
                local_dir = "session_media/av_studio/sfx"
                os.makedirs(local_dir, exist_ok=True)
                local_path = os.path.join(local_dir, filename)

                with open(local_path, "wb") as f:
                    f.write(audio_bytes)

                gcs_folder = tool_context.state.get("gcs_folder", "default")
                destination_blob = f"{gcs_folder}/av_studio/sfx/{filename}"
                upload_blob_to_gcs(
                    source_file_name=local_path,
                    destination_blob_name=destination_blob,
                )

                bucket_name = get_gcs_bucket().replace("gs://", "")
                gcs_uri = f"gs://{bucket_name}/{destination_blob}"

                generated_effects.append({
                    "effect_name": effect_name,
                    "gcs_uri": gcs_uri,
                    "local_path": local_path,
                })

                logging.info(f"Generated sound effect '{effect_name}' at {gcs_uri}")

        return {
            "status": "ok",
            "effects": generated_effects,
            "total_effects": len(generated_effects),
        }

    except Exception as e:
        logging.error(f"Error generating sound effects: {e}")
        return {"status": "failed", "error": str(e)}


def combine_audio_with_video(
    video_gcs_uri: str,
    music_gcs_uri: str,
    output_name: str,
    tool_context: ToolContext,
    sfx_config: Optional[Dict[str, Any]] = None,
) -> dict:
    """Combines generated music and sound effects with the video.

    Uses ffmpeg to merge the silent video with the generated soundtrack
    and any sound effects at specified timestamps.

    Args:
        video_gcs_uri (str): GCS URI of the video file (should be silent).
        music_gcs_uri (str): GCS URI of the background music.
        output_name (str): Name for the final output file.
        tool_context (ToolContext): The tool context.
        sfx_config (dict, optional): Configuration for sound effects placement.
            Format: {"effects": [{"gcs_uri": "...", "timestamp": 5.5}, ...]}

    Returns:
        dict: Status and final video with audio GCS URI.
    """
    try:
        import subprocess
        import tempfile
        from ...shared_libraries.utils import download_blob
        from google.cloud import storage

        storage_client = storage.Client()
        bucket_name = get_gcs_bucket().replace("gs://", "")

        # Download video and music
        video_blob = video_gcs_uri.replace(f"gs://{bucket_name}/", "")
        music_blob = music_gcs_uri.replace(f"gs://{bucket_name}/", "")

        video_bytes = download_blob(bucket_name, video_blob)
        music_bytes = download_blob(bucket_name, music_blob)

        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = os.path.join(tmp_dir, "video.mp4")
            # Detect audio extension from GCS URI (Lyria 2 outputs .wav)
            music_ext = os.path.splitext(music_gcs_uri)[1] or ".wav"
            music_path = os.path.join(tmp_dir, f"music{music_ext}")
            output_path = os.path.join(tmp_dir, f"{output_name}.mp4")

            with open(video_path, "wb") as f:
                f.write(video_bytes)
            with open(music_path, "wb") as f:
                f.write(music_bytes)

            # Build ffmpeg command
            if sfx_config and sfx_config.get("effects"):
                # Complex audio mixing with SFX
                filter_complex = f"[1:a]volume=0.8[music]"  # Reduce music volume
                inputs = ["-i", video_path, "-i", music_path]

                # Add each SFX as input
                for i, effect in enumerate(sfx_config["effects"], start=2):
                    sfx_blob = effect["gcs_uri"].replace(f"gs://{bucket_name}/", "")
                    sfx_bytes = download_blob(bucket_name, sfx_blob)
                    sfx_path = os.path.join(tmp_dir, f"sfx_{i}.wav")
                    with open(sfx_path, "wb") as f:
                        f.write(sfx_bytes)
                    inputs.extend(["-i", sfx_path])

                    # Add delay filter for timing
                    timestamp_ms = int(effect["timestamp"] * 1000)
                    filter_complex += f";[{i}:a]adelay={timestamp_ms}|{timestamp_ms}[sfx{i}]"

                # Mix all audio streams
                mix_inputs = "[music]"
                for i in range(2, 2 + len(sfx_config["effects"])):
                    mix_inputs += f"[sfx{i}]"
                filter_complex += f";{mix_inputs}amix=inputs={1 + len(sfx_config['effects'])}:duration=first[final]"

                cmd = inputs + [
                    "-filter_complex", filter_complex,
                    "-map", "0:v",
                    "-map", "[final]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    output_path
                ]
            else:
                # Simple audio replacement
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-i", music_path,
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    output_path
                ]

            # Execute ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {"status": "failed", "error": f"ffmpeg error: {result.stderr}"}

            # Upload final video
            with open(output_path, "rb") as f:
                output_bytes = f.read()

            # Save locally
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

            logging.info(f"Created final video with audio at {final_gcs_uri}")

            return {
                "status": "ok",
                "gcs_uri": final_gcs_uri,
                "local_path": local_final,
                "has_music": True,
                "has_sfx": bool(sfx_config and sfx_config.get("effects")),
            }

    except Exception as e:
        logging.error(f"Error combining audio with video: {e}")
        return {"status": "failed", "error": str(e)}