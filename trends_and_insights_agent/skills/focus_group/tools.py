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
PANELIST_VOICES = {
    "young_female": {
        "language_code": "en-US",
        "name": "en-US-Chirp3-HD-Aoede",
        "description": "Young, enthusiastic female voice",
    },
    "young_male": {
        "language_code": "en-US",
        "name": "en-US-Chirp3-HD-Charon",
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

    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=config.image_gen_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            break
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < 2:
                wait = 15 * (attempt + 1)
                logging.warning(f"Portrait gen rate limited, waiting {wait}s (attempt {attempt + 1}/3)")
                time.sleep(wait)
            else:
                logging.error(f"Panelist portrait generation failed: {e}")
                return {"status": "failed", "error": str(e)}

    if not response or not response.candidates or not response.candidates[0].content.parts:
        return {"status": "failed", "error": "No image data in response"}

    safe_name = panelist_name.replace(" ", "_").replace(",", "")
    artifact_key = f"panelist_{safe_name}.png"

    local_dir = "session_media/focus_group/portraits"
    os.makedirs(local_dir, exist_ok=True)

    for part in response.candidates[0].content.parts:
        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
            image_bytes = part.inline_data.data

            await tool_context.save_artifact(
                filename=artifact_key,
                artifact=types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            )

            local_path = os.path.join(local_dir, artifact_key)
            with open(local_path, "wb") as f:
                f.write(image_bytes)

            gcs_folder = tool_context.state.get("gcs_folder", "default")
            destination_blob = f"{gcs_folder}/focus_group/{artifact_key}"
            upload_blob_to_gcs(
                source_file_name=local_path,
                destination_blob_name=destination_blob,
            )

            bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
            gcs_uri = f"{bucket}/{destination_blob}"

            logging.info(f"Generated panelist portrait: {artifact_key}")

            # Store panelist portrait metadata in state
            panelists = tool_context.state.get("focus_group_panelists", {"panelists": []})
            panelists["panelists"].append({
                "name": panelist_name,
                "age": age,
                "persona": persona_description,
                "portrait_artifact": artifact_key,
                "portrait_gcs_uri": gcs_uri,
            })
            tool_context.state["focus_group_panelists"] = panelists

            return {
                "status": "ok",
                "artifact_key": artifact_key,
                "gcs_uri": gcs_uri,
                "panelist_name": panelist_name,
            }

    return {"status": "failed", "error": "No image data in response parts"}


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

    # Step 2: Generate video from portrait reference + prompt
    from google.genai.types import GenerateVideosConfig, VideoGenerationReferenceImage

    portrait_gcs_uri = panelist_data.get("portrait_gcs_uri", "")
    video_prompt = (
        f"<SUBJECT> A {panelist_data.get('age', 25)}-year-old person, the same person "
        f"from the reference image, speaking directly to camera with natural gestures. "
        f"<ACTION> The person is talking naturally, making eye contact with the camera, "
        f"occasionally nodding and using subtle hand gestures. Their expression is "
        f"engaged and genuine. "
        f"<SCENE_AND_CONTEXT> A modern, well-lit focus group room or home office. "
        f"Clean background, soft lighting. "
        f"<CAMERA_ANGLE> Medium close-up, shoulders and head. "
        f"<CAMERA_MOVEMENTS> Static, locked-off camera. "
        f"<VISUAL_STYLE_AND_AESTHETICS> Natural, documentary style. High quality. "
        f"SUPPRESS SUBTITLES."
    )

    try:
        reference_images = None
        if portrait_gcs_uri:
            reference_images = [
                VideoGenerationReferenceImage(
                    image=types.Image(gcs_uri=portrait_gcs_uri, mime_type="image/png"),
                    reference_type="STYLE",
                )
            ]

        gen_config = GenerateVideosConfig(
            aspect_ratio="16:9",
            number_of_videos=1,
            output_gcs_uri=os.environ.get("BUCKET", "gs://zghost-media-center"),
            reference_images=reference_images,
        )

        operation = client.models.generate_videos(
            model=config.video_gen_model, prompt=video_prompt, config=gen_config
        )
        while not operation.done:
            time.sleep(15)
            operation = client.operations.get(operation)

        if operation.error:
            # Retry without reference image
            logging.warning(f"Video gen with reference failed: {operation.error}. Retrying without reference.")
            gen_config_no_ref = GenerateVideosConfig(
                aspect_ratio="16:9",
                number_of_videos=1,
                output_gcs_uri=os.environ.get("BUCKET", "gs://zghost-media-center"),
            )
            operation = client.models.generate_videos(
                model=config.video_gen_model, prompt=video_prompt, config=gen_config_no_ref
            )
            while not operation.done:
                time.sleep(15)
                operation = client.operations.get(operation)

        if operation.error:
            return {"status": "failed", "error": f"Video generation failed: {operation.error}"}

        video_artifact_key = None
        if operation.result and operation.result.generated_videos:
            for idx, gen_video in enumerate(operation.result.generated_videos):
                if gen_video.video and gen_video.video.uri:
                    video_uri = gen_video.video.uri
                    video_artifact_key = f"panelist_testimonial_{safe_name}_{idx}.mp4"

                    bucket_name = os.environ.get("BUCKET", "gs://zghost-media-center").replace("gs://", "")
                    source_blob = video_uri.replace(f"gs://{bucket_name}/", "")

                    from ...shared_libraries.utils import download_blob
                    video_bytes = download_blob(
                        bucket_name=bucket_name, source_blob_name=source_blob
                    )

                    await tool_context.save_artifact(
                        filename=video_artifact_key,
                        artifact=types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
                    )

                    dest_blob = f"{gcs_folder}/focus_group/{video_artifact_key}"
                    bucket_obj = storage_client.get_bucket(bucket_name)
                    source_blob_obj = bucket_obj.blob(source_blob)
                    bucket_obj.copy_blob(source_blob_obj, bucket_obj, new_name=dest_blob)

                    video_gcs_uri = f"gs://{bucket_name}/{dest_blob}"
                    logging.info(f"Generated panelist testimonial video: {video_artifact_key}")
                    break

        if not video_artifact_key:
            return {"status": "partial", "voiceover_gcs_uri": vo_gcs_uri, "error": "Video generation produced no output"}

        # Update panelist data in state
        for p in panelists.get("panelists", []):
            if p["name"] == panelist_name:
                p["testimonial_video_artifact"] = video_artifact_key
                p["testimonial_video_gcs_uri"] = video_gcs_uri
                p["voiceover_gcs_uri"] = vo_gcs_uri
                break
        tool_context.state["focus_group_panelists"] = panelists

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
