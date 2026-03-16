"""Focus group tools: video analysis, panelist portrait generation, and Chirp voiceover testimonials."""

import logging
import os
import uuid
import time
from typing import List, Dict, Any

from google import genai
from google.genai import types
from google.cloud import texttospeech_v1beta1 as texttospeech
from google.cloud import storage
from google.adk.tools import ToolContext

from ...shared_libraries.config import config
from ...shared_libraries.utils import upload_blob_to_gcs

logging.basicConfig(level=logging.INFO)

client = genai.Client()
tts_client = texttospeech.TextToSpeechClient()
storage_client = storage.Client()

# Chirp voice presets for diverse panelist personas
# Each voice is unique to avoid all panelists sounding alike
PANELIST_VOICES = {
    "young_female": {
        "language_code": "en-US",
        "name": "en-US-Chirp3-HD-Leda",
        "description": "Young, enthusiastic female voice",
    },
    "young_male": {
        "language_code": "en-US",
        "name": "en-US-Chirp3-HD-Orus",
        "description": "Young, confident male voice",
    },
    "mature_female": {
        "language_code": "en-US",
        "name": "en-US-Chirp3-HD-Aoede",
        "description": "Mature, thoughtful female voice",
    },
    "mature_male": {
        "language_code": "en-US",
        "name": "en-US-Chirp3-HD-Charon",
        "description": "Mature, professional male voice",
    },
    "british_female": {
        "language_code": "en-GB",
        "name": "en-GB-Chirp3-HD-Aoede",
        "description": "British-accented female voice",
    },
}


def analyze_commercial_video(tool_context: ToolContext) -> dict:
    """Analyzes the 30-second commercial video using Gemini video understanding.

    Reads the commercial_artifact GCS URI from session state and sends
    the video to Gemini for detailed visual analysis including frame-by-frame
    description, character consistency, scene transitions, and production quality.

    Returns:
        dict with status and detailed analysis text.
    """
    commercial_artifact = tool_context.state.get("commercial_artifact")
    if not commercial_artifact:
        return {
            "status": "failed",
            "error": "No commercial_artifact found in session state. "
            "The commercial must be produced before running focus group evaluation.",
        }

    gcs_uri = commercial_artifact.get("gcs_uri", "")
    if not gcs_uri:
        return {
            "status": "failed",
            "error": "commercial_artifact has no gcs_uri.",
        }

    try:
        video = types.Part.from_uri(
            file_uri=gcs_uri,
            mime_type="video/mp4",
        )

        analysis_prompt = """You are a professional video production analyst. Analyze this 30-second commercial video in detail:

1. **Frame-by-Frame Visual Description**: Describe what happens in each major scene/shot transition. Note camera angles, movements, and compositions.

2. **Character Consistency Assessment**: Evaluate whether characters maintain consistent appearance (clothing, hair, features) across all scenes. Note any inconsistencies.

3. **Scene Transition Quality**: Rate the smoothness of transitions between scenes. Are they jarring or seamless? Do the visual elements flow naturally from one scene to the next?

4. **Visual Quality and Production Value**: Assess the overall visual fidelity - lighting, color grading, resolution, and any artifacts or quality issues.

5. **Product Visibility and Placement**: Identify where and how the product appears. Is it naturally integrated or forced? Is the brand clearly visible?

Provide your analysis in a structured format with clear sections for each category above."""

        contents = types.Content(
            role="user",
            parts=[types.Part.from_text(text=analysis_prompt), video],
        )

        result = client.models.generate_content(
            model=config.video_analysis_model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1),
        )

        if result and result.text:
            return {"status": "ok", "analysis": result.text}
        else:
            return {
                "status": "failed",
                "error": "Gemini returned empty analysis for the video.",
            }

    except Exception as e:
        logging.error(f"Failed to analyze commercial video: {e}")
        return {"status": "failed", "error": str(e)}


async def generate_panelist_portrait(
    panelist_name: str,
    age: int,
    persona_description: str,
    tool_context: ToolContext,
) -> dict:
    """Generates a realistic portrait photo of a focus group panelist persona.

    Creates a professional headshot-style image matching the panelist's
    demographic profile and persona description.

    Args:
        panelist_name: The panelist's name (e.g., "Maya Chen").
        age: The panelist's age.
        persona_description: Brief persona description (e.g., "Gen Z college student,
            eco-conscious, loves thrift shopping and plant-based living").
        tool_context: The tool context.

    Returns:
        dict with status, artifact_key of the generated portrait, and GCS URI.
    """
    prompt = (
        f"Professional headshot photograph of a {age}-year-old person matching this "
        f"consumer persona: {persona_description}. "
        f"Natural lighting, friendly genuine smile, neutral soft-focus background. "
        f"High-quality portrait photography, 4K resolution. "
        f"The person should look approachable and authentic, NOT like a stock photo. "
        f"Style: modern consumer research panel participant photo."
    )

    safe_name = panelist_name.replace(" ", "_").replace(",", "")
    artifact_key = f"panelist_{safe_name}.png"
    local_dir = "session_media/focus_group/portraits"
    os.makedirs(local_dir, exist_ok=True)

    gcs_folder = tool_context.state.get("gcs_folder", "default")
    bucket = os.environ.get("BUCKET", "gs://zghost-media-center")

    # Use Imagen 4 generate_images() — synchronous, reliable on AE
    from google.genai.types import GenerateImagesConfig
    img_client = genai.Client(vertexai=True)
    image_bytes = None
    gcs_uri = ""

    for attempt in range(3):
        try:
            output_gcs = f"{bucket}/{gcs_folder}" if bucket and gcs_folder else None
            img_config = GenerateImagesConfig(
                number_of_images=1,
                **({"output_gcs_uri": output_gcs} if output_gcs else {}),
            )
            response = img_client.models.generate_images(
                model="imagen-4.0-generate-preview-06-06",
                prompt=prompt,
                config=img_config,
            )
            if response and response.generated_images:
                gen_img = response.generated_images[0]
                image_bytes = gen_img.image.image_bytes if gen_img.image else None
                if output_gcs and hasattr(gen_img, 'gcs_uri') and gen_img.gcs_uri:
                    gcs_uri = gen_img.gcs_uri
                break
            else:
                logging.warning(f"Portrait gen returned empty (attempt {attempt + 1}/3)")
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < 2:
                wait = 15 * (attempt + 1)
                logging.warning(f"Portrait gen rate limited, waiting {wait}s (attempt {attempt + 1}/3)")
                time.sleep(wait)
            else:
                logging.error(f"Panelist portrait generation failed: {e}")
                return {"status": "failed", "error": str(e)}

    if not image_bytes:
        return {"status": "failed", "error": "No image data from Imagen 4"}

    # Save locally
    local_path = os.path.join(local_dir, artifact_key)
    with open(local_path, "wb") as f:
        f.write(image_bytes)

    # Upload to GCS if not already there
    if not gcs_uri:
        destination_blob = f"{gcs_folder}/focus_group/{artifact_key}"
        upload_blob_to_gcs(
            source_file_name=local_path,
            destination_blob_name=destination_blob,
        )
        gcs_uri = f"{bucket}/{destination_blob}"

    # Save as ADK artifact
    await tool_context.save_artifact(
        filename=artifact_key,
        artifact=types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
    )

    logging.info(f"Generated panelist portrait via Imagen 4: {artifact_key}")

    # Store panelist portrait metadata in state (new dict for AE persistence)
    panelists = tool_context.state.get("focus_group_panelists", {"panelists": []})
    new_panelist = {
        "name": panelist_name,
        "age": age,
        "persona": persona_description,
        "portrait_artifact": artifact_key,
        "portrait_gcs_uri": gcs_uri,
    }
    new_list = list(panelists.get("panelists", [])) + [new_panelist]
    tool_context.state["focus_group_panelists"] = {"panelists": new_list}

    return {
        "status": "ok",
        "artifact_key": artifact_key,
        "gcs_uri": gcs_uri,
        "panelist_name": panelist_name,
    }


async def generate_panelist_testimonial(
    panelist_name: str,
    testimonial_script: str,
    voice_style: str,
    tool_context: ToolContext,
    speaking_rate: float = 1.0,
) -> dict:
    """Generates a video testimonial of a panelist speaking their feedback.

    Creates a video by:
    1. Using the panelist's previously generated portrait as the reference image
    2. Generating Chirp 3 HD voiceover of their testimonial script
    3. Generating a video using Veo with the portrait as reference

    The panelist portrait must have been generated first with generate_panelist_portrait.

    Args:
        panelist_name: The panelist's name (must match a previously generated portrait).
        testimonial_script: The panelist's spoken feedback/testimonial text.
            Keep under 100 words for a natural video clip.
        voice_style: Voice preset from PANELIST_VOICES (e.g., "young_female",
            "mature_male", "british_female").
        tool_context: The tool context.
        speaking_rate: Speed of speech (0.8-1.2 recommended). Defaults to 1.0.

    Returns:
        dict with status, voiceover GCS URI, video artifact_key, and metadata.
    """
    # Find the panelist's portrait from state
    panelists = tool_context.state.get("focus_group_panelists", {"panelists": []})
    panelist_data = None
    for p in panelists.get("panelists", []):
        if p["name"] == panelist_name:
            panelist_data = p
            break

    if not panelist_data:
        return {
            "status": "failed",
            "error": f"No portrait found for panelist '{panelist_name}'. "
            "Call generate_panelist_portrait first.",
        }

    # Step 1: Generate Chirp voiceover
    if voice_style not in PANELIST_VOICES:
        voice_style = "young_female"  # default fallback

    voice_config = PANELIST_VOICES[voice_style]

    try:
        ssml_script = f"""<speak>
            <prosody rate="{speaking_rate}">
                {testimonial_script}
            </prosody>
        </speak>"""

        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config["language_code"],
            name=voice_config["name"],
        )
        audio_cfg = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            sample_rate_hertz=48000,
        )
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_script)
        request = texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_cfg,
        )

        response = tts_client.synthesize_speech(request=request)
        audio_content = response.audio_content

        safe_name = panelist_name.replace(" ", "_").replace(",", "")
        vo_filename = f"panelist_vo_{safe_name}_{str(uuid.uuid4())[:6]}.mp3"
        local_dir = "session_media/focus_group/voiceover"
        os.makedirs(local_dir, exist_ok=True)
        vo_local_path = os.path.join(local_dir, vo_filename)

        with open(vo_local_path, "wb") as f:
            f.write(audio_content)

        gcs_folder = tool_context.state.get("gcs_folder", "default")
        vo_destination = f"{gcs_folder}/focus_group/voiceover/{vo_filename}"
        upload_blob_to_gcs(
            source_file_name=vo_local_path,
            destination_blob_name=vo_destination,
        )

        bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
        vo_gcs_uri = f"{bucket}/{vo_destination}"
        logging.info(f"Generated panelist voiceover: {vo_gcs_uri}")

    except Exception as e:
        logging.error(f"Panelist voiceover generation failed: {e}")
        return {"status": "failed", "error": f"Voiceover generation failed: {e}"}

    # Step 2: Create Ken Burns zoom video from portrait + voiceover audio
    import subprocess

    portrait_gcs_uri = panelist_data.get("portrait_gcs_uri", "")
    testimonial_duration = int(tool_context.state.get("testimonial_duration", 15))

    try:
        # Download portrait image
        portrait_local = None
        if portrait_gcs_uri:
            bucket_name = os.environ.get("BUCKET", "gs://zghost-media-center").replace("gs://", "")
            portrait_blob = portrait_gcs_uri.replace(f"gs://{bucket_name}/", "")
            from ...shared_libraries.utils import download_blob
            portrait_bytes = download_blob(bucket_name=bucket_name, source_blob_name=portrait_blob)
            portrait_dir = "session_media/focus_group/portraits"
            os.makedirs(portrait_dir, exist_ok=True)
            portrait_local = os.path.join(portrait_dir, f"{safe_name}_portrait.png")
            with open(portrait_local, "wb") as f:
                f.write(portrait_bytes)

        if not portrait_local or not os.path.exists(portrait_local):
            return {"status": "partial", "voiceover_gcs_uri": vo_gcs_uri, "error": "No portrait image for Ken Burns"}

        # Ken Burns zoom effect: slow zoom in on the portrait with the voiceover
        video_artifact_key = f"panelist_testimonial_{safe_name}.mp4"
        video_dir = "session_media/focus_group/testimonials"
        os.makedirs(video_dir, exist_ok=True)
        video_local_path = os.path.join(video_dir, video_artifact_key)

        # Probe the audio duration so video matches voiceover exactly (no cutoff)
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", vo_local_path,
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        try:
            audio_duration = float(probe_result.stdout.strip())
        except (ValueError, AttributeError):
            audio_duration = float(testimonial_duration)
        # Add a small buffer so audio isn't clipped at the very end
        video_duration = audio_duration + 0.5

        # ffmpeg Ken Burns: pad portrait to 1:1 (no stretch), then zoompan
        # The portrait may be any aspect ratio — pad to square first, then
        # zoompan produces 1920x1080 output by centering the square on a
        # 16:9 canvas. This prevents horizontal stretching.
        fps = 30
        total_frames = int(video_duration * fps)
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", portrait_local,
            "-i", vo_local_path,
            "-filter_complex",
            (
                "[0:v]"
                "scale=3840:2160:force_original_aspect_ratio=decrease,"
                "pad=3840:2160:(ow-iw)/2:(oh-ih)/2:black,"
                f"zoompan=z='1+0.15*on/{total_frames}':"
                "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={total_frames}:s=1920x1080:fps={fps}"
                "[v]"
            ),
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-t", f"{video_duration:.2f}",
            "-pix_fmt", "yuv420p",
            video_local_path,
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logging.warning(f"ffmpeg Ken Burns failed: {result.stderr[:500]}")
            return {"status": "partial", "voiceover_gcs_uri": vo_gcs_uri, "error": f"Ken Burns video failed: {result.stderr[:200]}"}

        # Read video bytes
        with open(video_local_path, "rb") as f:
            video_bytes = f.read()

        # Save as ADK artifact
        await tool_context.save_artifact(
            filename=video_artifact_key,
            artifact=types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
        )

        # Upload to GCS
        dest_blob = f"{gcs_folder}/focus_group/{video_artifact_key}"
        upload_blob_to_gcs(
            source_file_name=video_local_path,
            destination_blob_name=dest_blob,
        )
        bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
        video_gcs_uri = f"{bucket}/{dest_blob}"
        logging.info(f"Generated panelist Ken Burns testimonial: {video_artifact_key}")

        # Update panelist data in state (create new dict for AE persistence)
        updated_panelists = []
        for p in panelists.get("panelists", []):
            if p["name"] == panelist_name:
                updated_p = dict(p)
                updated_p["testimonial_video_artifact"] = video_artifact_key
                updated_p["testimonial_video_gcs_uri"] = video_gcs_uri
                updated_p["voiceover_gcs_uri"] = vo_gcs_uri
                updated_panelists.append(updated_p)
            else:
                updated_panelists.append(p)
        tool_context.state["focus_group_panelists"] = {"panelists": updated_panelists}

        return {
            "status": "ok",
            "voiceover_gcs_uri": vo_gcs_uri,
            "video_artifact_key": video_artifact_key,
            "video_gcs_uri": video_gcs_uri,
            "panelist_name": panelist_name,
        }

    except Exception as e:
        logging.error(f"Panelist testimonial video generation failed: {e}")
        return {
            "status": "partial",
            "voiceover_gcs_uri": vo_gcs_uri,
            "error": f"Video generation failed: {e}",
        }


def _generate_lyria_background_music(brand: str, product: str, target_audience: str) -> bytes | None:
    """Generate soft background music via Lyria 2 for the focus group reel."""
    try:
        import google.auth
        import google.auth.transport.requests
        import requests as http_requests
        import base64

        credentials, _ = google.auth.default()
        credentials.refresh(google.auth.transport.requests.Request())

        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = "us-central1"
        lyria_model = "lyria-2-generate-001"
        endpoint = (
            f"https://{location}-aiplatform.googleapis.com/v1/"
            f"projects/{project_id}/locations/{location}/"
            f"publishers/google/models/{lyria_model}:predict"
        )

        prompt = (
            f"Soft ambient background music for a consumer focus group discussion. "
            f"Gentle, warm, professional atmosphere. Light piano and strings. "
            f"Brand: {brand}, product: {product}, audience: {target_audience}. "
            f"Subtle and supportive — should not overpower speaking voices."
        )

        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"negative_prompt": "vocals, lyrics, singing, speech, voice, loud, heavy bass"},
        }
        headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}
        response = http_requests.post(endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()
        predictions = result.get("predictions", [])
        if predictions:
            return base64.b64decode(predictions[0]["bytesBase64Encoded"])
    except Exception as e:
        logging.warning(f"Lyria background music generation failed (non-fatal): {e}")
    return None


async def concatenate_panelist_videos(tool_context: ToolContext) -> dict:
    """Concatenate all panelist testimonial videos into a polished focus group reel.

    Creates a cinematic reel by:
    1. Normalizing all Ken Burns testimonial clips to consistent format
    2. Concatenating with crossfade transitions between panelists
    3. Generating Lyria 2 background music (soft ambient)
    4. Mixing background music under the panelist voices at low volume

    Returns:
        dict with status, artifact_key, and gcs_uri of the combined video.
    """
    import subprocess
    from ...shared_libraries.utils import download_blob

    panelists = tool_context.state.get("focus_group_panelists", {})
    panelist_list = panelists.get("panelists", []) if isinstance(panelists, dict) else []
    gcs_folder = tool_context.state.get("gcs_folder", "default")
    bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
    bucket_name = bucket.replace("gs://", "")

    # Collect all testimonial video paths
    video_paths = []
    video_dir = "session_media/focus_group/testimonials"
    os.makedirs(video_dir, exist_ok=True)

    for p in panelist_list:
        video_uri = p.get("testimonial_video_gcs_uri", "")
        if not video_uri:
            continue
        blob_name = video_uri.replace(f"gs://{bucket_name}/", "")
        safe_name = p.get("name", "unknown").replace(" ", "_").replace(",", "")
        local_path = os.path.join(video_dir, f"concat_{safe_name}.mp4")
        try:
            video_bytes = download_blob(bucket_name=bucket_name, source_blob_name=blob_name)
            with open(local_path, "wb") as f:
                f.write(video_bytes)
            video_paths.append(local_path)
        except Exception as e:
            logging.warning(f"Could not download panelist video {safe_name}: {e}")

    if len(video_paths) < 2:
        return {"status": "skipped", "message": f"Need at least 2 videos to concatenate (found {len(video_paths)})"}

    output_artifact = "focus_group_reel.mp4"
    output_path = os.path.join(video_dir, output_artifact)

    try:
        # Step 1: Normalize all clips to consistent format
        normalized = []
        for i, vp in enumerate(video_paths):
            norm_path = os.path.join(video_dir, f"norm_{i}.mp4")
            norm_cmd = [
                "ffmpeg", "-y", "-i", vp,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-r", "30", "-s", "1920x1080",
                "-pix_fmt", "yuv420p",
                norm_path,
            ]
            subprocess.run(norm_cmd, capture_output=True, text=True, timeout=60)
            if os.path.exists(norm_path):
                normalized.append(norm_path)

        if not normalized:
            return {"status": "failed", "error": "No videos could be normalized"}

        # Step 2: Concatenate with crossfade transitions
        concat_list_path = os.path.join(video_dir, "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for np_path in normalized:
                f.write(f"file '{os.path.abspath(np_path)}'\n")

        concat_no_music = os.path.join(video_dir, "reel_no_music.mp4")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            concat_no_music,
        ]
        result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return {"status": "failed", "error": f"Concat failed: {result.stderr[:200]}"}

        # Step 3: Generate Lyria background music
        brand = tool_context.state.get("brand", "")
        product = tool_context.state.get("target_product", "")
        audience = tool_context.state.get("target_audience", "")

        logging.info("[FocusGroup] Generating Lyria background music for reel...")
        music_bytes = _generate_lyria_background_music(brand, product, audience)

        if music_bytes:
            # Step 4: Mix background music under voices
            music_path = os.path.join(video_dir, "bg_music.wav")
            with open(music_path, "wb") as f:
                f.write(music_bytes)

            # Mix: voices at full volume, music at 15% volume with fade in/out
            mix_cmd = [
                "ffmpeg", "-y",
                "-i", concat_no_music,
                "-i", music_path,
                "-filter_complex",
                (
                    "[1:a]volume=0.15,afade=t=in:st=0:d=2,afade=t=out:st=25:d=3[music];"
                    "[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[aout]"
                ),
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                output_path,
            ]
            result = subprocess.run(mix_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logging.warning(f"Music mix failed, using reel without music: {result.stderr[:200]}")
                # Fallback: use concatenated reel without music
                os.rename(concat_no_music, output_path)
            else:
                logging.info("[FocusGroup] Background music mixed into reel successfully")
        else:
            # No music available — use concatenated reel as-is
            os.rename(concat_no_music, output_path)
            logging.info("[FocusGroup] Proceeding without background music")

        with open(output_path, "rb") as f:
            reel_bytes = f.read()

        # Save as artifact
        await tool_context.save_artifact(
            filename=output_artifact,
            artifact=types.Part.from_bytes(data=reel_bytes, mime_type="video/mp4"),
        )

        # Upload to GCS
        dest_blob = f"{gcs_folder}/focus_group/{output_artifact}"
        upload_blob_to_gcs(source_file_name=output_path, destination_blob_name=dest_blob)
        reel_gcs_uri = f"{bucket}/{dest_blob}"

        # Store in state
        tool_context.state["focus_group_reel_gcs_uri"] = reel_gcs_uri
        tool_context.state["focus_group_reel_artifact"] = output_artifact

        has_music = music_bytes is not None
        logging.info(
            f"Focus group reel created: {reel_gcs_uri} "
            f"({len(video_paths)} panelists, music={'YES' if has_music else 'NO'})"
        )

        # Cleanup temp files
        for np_path in normalized:
            try:
                os.unlink(np_path)
            except OSError:
                pass
        for tmp in [concat_no_music, os.path.join(video_dir, "bg_music.wav")]:
            try:
                os.unlink(tmp)
            except OSError:
                pass

        return {
            "status": "ok",
            "artifact_key": output_artifact,
            "gcs_uri": reel_gcs_uri,
            "panelist_count": len(video_paths),
            "has_background_music": has_music,
        }

    except Exception as e:
        logging.error(f"Focus group reel concatenation failed: {e}")
        return {"status": "failed", "error": str(e)}
