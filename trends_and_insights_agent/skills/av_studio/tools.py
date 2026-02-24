import cv2
import logging
import subprocess
import tempfile
import time
import os
import uuid

from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext
from google.genai.types import GenerateVideosConfig

from ...shared_libraries.config import config
from ...shared_libraries.utils import (
    download_blob,
    upload_blob_to_gcs,
    download_image_from_gcs,
)

logging.basicConfig(level=logging.INFO)

try:
    GCS_BUCKET = os.environ["BUCKET"]
except KeyError:
    raise Exception("BUCKET environment variable not set")

client = genai.Client()
storage_client = storage.Client()


def generate_subject_image(
    prompt: str,
    subject_name: str,
    tool_context: ToolContext,
) -> dict:
    """Generates a reference image for a subject (character, prop, scene) using Gemini native image generation.

    Use this tool to create visual reference images that establish consistent characters,
    props, or settings across multiple video clips in the commercial.

    Args:
        prompt (str): A detailed description of the subject to generate. Be specific about
            appearance, pose, lighting, and style for visual consistency.
        subject_name (str): A short, descriptive name for the subject (e.g., "hero_character",
            "product_closeup", "city_backdrop"). Used for file naming.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and paths. Keys: "status", "gcs_uri", "local_path", "subject_name".
    """
    try:
        response = client.models.generate_content(
            model=config.subject_image_gen_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        if not response.candidates or not response.candidates[0].content.parts:
            return {"status": "failed", "error": "No image generated"}

        image_part = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image_part = part
                break

        if image_part is None:
            return {"status": "failed", "error": "No image data in response"}

        image_bytes = image_part.inline_data.data
        mime_type = image_part.inline_data.mime_type
        ext = "png" if "png" in mime_type else "jpg"

        safe_name = subject_name.replace(" ", "_").replace(",", "")
        filename = f"{safe_name}_{str(uuid.uuid4())[:8]}.{ext}"

        local_dir = "session_media/av_studio/subjects"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        with open(local_path, "wb") as f:
            f.write(image_bytes)

        gcs_folder = tool_context.state.get("gcs_folder", "default")
        destination_blob = f"{gcs_folder}/av_studio/subjects/{filename}"
        upload_blob_to_gcs(
            source_file_name=local_path,
            destination_blob_name=destination_blob,
        )

        bucket_name = GCS_BUCKET.replace("gs://", "")
        gcs_uri = f"gs://{bucket_name}/{destination_blob}"

        logging.info(f"Generated subject image '{subject_name}' at {gcs_uri}")

        return {
            "status": "ok",
            "gcs_uri": gcs_uri,
            "local_path": local_path,
            "subject_name": subject_name,
        }

    except Exception as e:
        logging.error(f"Error generating subject image: {e}")
        return {"status": "failed", "error": str(e)}


def generate_clip_with_frames(
    prompt: str,
    clip_name: str,
    first_frame_gcs_uri: str,
    tool_context: ToolContext,
    last_frame_gcs_uri: str = "",
    reference_image_gcs_uris: list[str] | None = None,
) -> dict:
    """Generates an 8-second video clip using Veo with first-frame (and optional last-frame) conditioning.

    Use this tool to generate each clip in the commercial chain. The first clip uses a subject
    reference image as its first frame. Subsequent clips use the last frame of the previous clip
    as their first frame to ensure visual continuity.

    Args:
        prompt (str): A detailed prompt describing the action, camera movement, and mood for the clip.
        clip_name (str): A short name for this clip (e.g., "clip_1_opening", "clip_2_action").
            Used for file naming.
        first_frame_gcs_uri (str): GCS URI of the image to use as the first frame
            (e.g., "gs://bucket/path/to/image.png"). Required for visual continuity.
        tool_context (ToolContext): The tool context.
        last_frame_gcs_uri (str, optional): GCS URI of the image to use as the last frame.
            If provided, the video will transition toward this image. Defaults to "".
        reference_image_gcs_uris (list[str], optional): List of GCS URIs for character/object
            reference images to maintain visual consistency across clips. These images guide
            Veo to preserve character appearance throughout the commercial. Defaults to [].

    Returns:
        dict: Status and paths. Keys: "status", "gcs_uri", "local_path", "clip_name".
    """
    try:
        safe_name = clip_name.replace(" ", "_").replace(",", "")
        filename = f"{safe_name}_{str(uuid.uuid4())[:8]}.mp4"

        gen_config = GenerateVideosConfig(
            aspect_ratio="16:9",
            number_of_videos=1,
            output_gcs_uri=GCS_BUCKET,
        )

        if last_frame_gcs_uri:
            gen_config.last_frame = types.Image(
                gcs_uri=last_frame_gcs_uri, mime_type="image/png"
            )

        # Build reference images for character consistency
        if reference_image_gcs_uris is None:
            reference_image_gcs_uris = []
        if reference_image_gcs_uris:
            reference_images = []
            for ref_uri in reference_image_gcs_uris:
                ref_image = types.Image(gcs_uri=ref_uri, mime_type="image/png")
                reference_images.append(
                    types.VideoGenerationReferenceImage(
                        image=ref_image,
                        reference_type="asset",
                    )
                )
            gen_config.reference_images = reference_images

        first_frame_image = types.Image(
            gcs_uri=first_frame_gcs_uri, mime_type="image/png"
        )

        operation = client.models.generate_videos(
            model=config.video_gen_model,
            prompt=prompt,
            image=first_frame_image,
            config=gen_config,
        )

        while not operation.done:
            time.sleep(15)
            operation = client.operations.get(operation)
            logging.info(f"Clip '{clip_name}' generation status: {operation}")

        if operation.error:
            return {"status": "failed", "error": str(operation.error)}

        if (
            operation.result is not None
            and operation.result.generated_videos is not None
        ):
            for generated_video in operation.result.generated_videos:
                if (
                    generated_video.video is not None
                    and generated_video.video.uri is not None
                ):
                    video_uri = generated_video.video.uri

                    bucket_name = GCS_BUCKET.replace("gs://", "")
                    source_blob = video_uri.replace(GCS_BUCKET, "").lstrip("/")

                    video_bytes = download_blob(
                        bucket_name=bucket_name, source_blob_name=source_blob
                    )

                    local_dir = "session_media/av_studio/clips"
                    os.makedirs(local_dir, exist_ok=True)
                    local_path = os.path.join(local_dir, filename)

                    with open(local_path, "wb") as f:
                        f.write(video_bytes)

                    gcs_folder = tool_context.state.get("gcs_folder", "default")
                    destination_blob = f"{gcs_folder}/av_studio/clips/{filename}"

                    # Copy to organized GCS location
                    bucket_obj = storage_client.get_bucket(bucket_name)
                    src_blob_obj = bucket_obj.blob(source_blob)
                    bucket_obj.copy_blob(
                        src_blob_obj, bucket_obj, new_name=destination_blob
                    )

                    gcs_uri = f"gs://{bucket_name}/{destination_blob}"
                    logging.info(f"Generated clip '{clip_name}' at {gcs_uri}")

                    return {
                        "status": "ok",
                        "gcs_uri": gcs_uri,
                        "local_path": local_path,
                        "clip_name": clip_name,
                    }

        return {"status": "failed", "error": "No video generated in response"}

    except Exception as e:
        logging.error(f"Error generating clip '{clip_name}': {e}")
        return {"status": "failed", "error": str(e)}


def extract_frame_from_clip(
    video_gcs_uri: str,
    frame_position: str,
    output_name: str,
    tool_context: ToolContext,
) -> dict:
    """Extracts the first or last frame from a video clip and uploads it to GCS.

    Use this tool to extract the last frame of a completed clip so it can be used as the
    first frame of the next clip, ensuring visual continuity in the clip chain.

    Args:
        video_gcs_uri (str): GCS URI of the video to extract a frame from
            (e.g., "gs://bucket/path/to/clip.mp4").
        frame_position (str): Which frame to extract. Must be "first" or "last".
        output_name (str): Name for the extracted frame file (e.g., "clip1_last_frame").
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and paths. Keys: "status", "gcs_uri", "local_path".
    """
    try:
        bucket_name = GCS_BUCKET.replace("gs://", "")
        source_blob = video_gcs_uri.replace(f"gs://{bucket_name}/", "")

        local_dir = "session_media/av_studio/frames"
        os.makedirs(local_dir, exist_ok=True)

        safe_name = output_name.replace(" ", "_").replace(",", "")
        local_video_path = os.path.join(local_dir, f"{safe_name}_video.mp4")
        local_frame_path = os.path.join(local_dir, f"{safe_name}.png")

        download_image_from_gcs(
            source_blob_name=source_blob,
            destination_file_name=local_video_path,
            gcs_bucket=bucket_name,
        )

        cap = cv2.VideoCapture(local_video_path)
        if not cap.isOpened():
            return {
                "status": "failed",
                "error": f"Could not open video file {local_video_path}",
            }

        if frame_position == "last":
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_number = max(0, total_frames - 1)
        else:
            frame_number = 0

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return {
                "status": "failed",
                "error": f"Could not read frame {frame_number} from video",
            }

        cv2.imwrite(local_frame_path, frame)

        gcs_folder = tool_context.state.get("gcs_folder", "default")
        destination_blob = f"{gcs_folder}/av_studio/frames/{safe_name}.png"
        upload_blob_to_gcs(
            source_file_name=local_frame_path,
            destination_blob_name=destination_blob,
        )

        gcs_uri = f"gs://{bucket_name}/{destination_blob}"
        logging.info(
            f"Extracted {frame_position} frame from clip, saved to {gcs_uri}"
        )

        # Clean up local video file (keep frame for reference)
        if os.path.exists(local_video_path):
            os.remove(local_video_path)

        return {
            "status": "ok",
            "gcs_uri": gcs_uri,
            "local_path": local_frame_path,
        }

    except Exception as e:
        logging.error(f"Error extracting frame: {e}")
        return {"status": "failed", "error": str(e)}


def concatenate_clips(
    clip_gcs_uris: list[str],
    output_name: str,
    tool_context: ToolContext,
) -> dict:
    """Concatenates multiple video clips into a single video using ffmpeg.

    Use this tool after all 4 clips have been generated to join them into a single
    continuous video. The clips are concatenated in the order provided.

    Args:
        clip_gcs_uris (list[str]): Ordered list of GCS URIs for the clips to concatenate
            (e.g., ["gs://bucket/clip1.mp4", "gs://bucket/clip2.mp4", ...]).
        output_name (str): Name for the concatenated output file (e.g., "commercial_raw").
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and paths. Keys: "status", "gcs_uri", "local_path", "duration_seconds".
    """
    if not clip_gcs_uris:
        return {"status": "failed", "error": "No clip URIs provided"}

    try:
        bucket_name = GCS_BUCKET.replace("gs://", "")

        with tempfile.TemporaryDirectory() as temp_dir:
            local_clip_paths = []
            for idx, gcs_uri in enumerate(clip_gcs_uris):
                source_blob = gcs_uri.replace(f"gs://{bucket_name}/", "")
                local_path = os.path.join(temp_dir, f"clip_{idx}.mp4")
                download_image_from_gcs(
                    source_blob_name=source_blob,
                    destination_file_name=local_path,
                    gcs_bucket=bucket_name,
                )
                local_clip_paths.append(local_path)

            # Create ffmpeg concat file list
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_path, "w") as f:
                for clip_path in local_clip_paths:
                    f.write(f"file '{clip_path}'\n")

            safe_name = output_name.replace(" ", "_").replace(",", "")
            output_filename = f"{safe_name}_{str(uuid.uuid4())[:8]}.mp4"
            output_path = os.path.join(temp_dir, output_filename)

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_path,
                    "-c", "copy",
                    output_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            # Get duration
            probe_result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    output_path,
                ],
                capture_output=True,
                text=True,
            )
            duration = float(probe_result.stdout.strip()) if probe_result.stdout.strip() else 0

            # Copy to persistent local dir
            local_dir = "session_media/av_studio"
            os.makedirs(local_dir, exist_ok=True)
            local_final_path = os.path.join(local_dir, output_filename)

            with open(output_path, "rb") as src, open(local_final_path, "wb") as dst:
                dst.write(src.read())

            gcs_folder = tool_context.state.get("gcs_folder", "default")
            destination_blob = f"{gcs_folder}/av_studio/{output_filename}"
            upload_blob_to_gcs(
                source_file_name=local_final_path,
                destination_blob_name=destination_blob,
            )

            gcs_uri = f"gs://{bucket_name}/{destination_blob}"
            logging.info(
                f"Concatenated {len(clip_gcs_uris)} clips into {gcs_uri} ({duration:.1f}s)"
            )

            return {
                "status": "ok",
                "gcs_uri": gcs_uri,
                "local_path": local_final_path,
                "duration_seconds": round(duration, 1),
            }

    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg concat error: {e.stderr}")
        return {"status": "failed", "error": f"FFmpeg error: {e.stderr}"}
    except Exception as e:
        logging.error(f"Error concatenating clips: {e}")
        return {"status": "failed", "error": str(e)}


def trim_video(
    video_gcs_uri: str,
    target_duration_seconds: int,
    output_name: str,
    tool_context: ToolContext,
) -> dict:
    """Trims a video to a target duration using ffmpeg.

    Use this tool after concatenation to trim the raw ~32-second video down to
    exactly 30 seconds for the final commercial.

    Args:
        video_gcs_uri (str): GCS URI of the video to trim (e.g., "gs://bucket/path/to/video.mp4").
        target_duration_seconds (int): Target duration in seconds (e.g., 30).
        output_name (str): Name for the trimmed output file (e.g., "commercial_30s").
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and paths. Keys: "status", "gcs_uri", "local_path", "duration_seconds".
    """
    try:
        bucket_name = GCS_BUCKET.replace("gs://", "")
        source_blob = video_gcs_uri.replace(f"gs://{bucket_name}/", "")

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.mp4")
            download_image_from_gcs(
                source_blob_name=source_blob,
                destination_file_name=input_path,
                gcs_bucket=bucket_name,
            )

            safe_name = output_name.replace(" ", "_").replace(",", "")
            output_filename = f"{safe_name}_{str(uuid.uuid4())[:8]}.mp4"
            output_path = os.path.join(temp_dir, output_filename)

            subprocess.run(
                [
                    "ffmpeg",
                    "-i", input_path,
                    "-t", str(target_duration_seconds),
                    "-c", "copy",
                    output_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            local_dir = "session_media/av_studio"
            os.makedirs(local_dir, exist_ok=True)
            local_final_path = os.path.join(local_dir, output_filename)

            with open(output_path, "rb") as src, open(local_final_path, "wb") as dst:
                dst.write(src.read())

            gcs_folder = tool_context.state.get("gcs_folder", "default")
            destination_blob = f"{gcs_folder}/av_studio/{output_filename}"
            upload_blob_to_gcs(
                source_file_name=local_final_path,
                destination_blob_name=destination_blob,
            )

            gcs_uri = f"gs://{bucket_name}/{destination_blob}"
            logging.info(
                f"Trimmed video to {target_duration_seconds}s, saved to {gcs_uri}"
            )

            return {
                "status": "ok",
                "gcs_uri": gcs_uri,
                "local_path": local_final_path,
                "duration_seconds": target_duration_seconds,
            }

    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg trim error: {e.stderr}")
        return {"status": "failed", "error": f"FFmpeg error: {e.stderr}"}
    except Exception as e:
        logging.error(f"Error trimming video: {e}")
        return {"status": "failed", "error": str(e)}


async def save_commercial_artifact(
    commercial_gcs_uri: str,
    commercial_metadata: dict,
    tool_context: ToolContext,
) -> dict:
    """Saves the final 30-second commercial as an ADK artifact and updates session state.

    Use this tool as the final step after trimming the commercial to 30 seconds.
    It downloads the finished commercial from GCS, saves it as an ADK artifact,
    and records metadata in the session state.

    Args:
        commercial_gcs_uri (str): GCS URI of the final trimmed commercial
            (e.g., "gs://bucket/path/to/commercial_30s.mp4").
        commercial_metadata (dict): Metadata about the commercial. Expected keys:
            title (str): A title for the commercial referencing both the trend and the product.
            scene_descriptions (list[str]): Brief descriptions of each scene, including which trend each connects to.
            total_clips (int): Number of clips used.
            duration_seconds (int): Final duration in seconds.
            trend_connections (str, optional): Which trends from target_search_trends and target_yt_trends informed the creative.
            narrative_arc (str, optional): A one-sentence summary of the commercial's story.
            target_audience_appeal (str, optional): Why this commercial will resonate with the target audience.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and artifact key. Keys: "status", "artifact_key".
    """
    try:
        bucket_name = GCS_BUCKET.replace("gs://", "")
        source_blob = commercial_gcs_uri.replace(f"gs://{bucket_name}/", "")

        video_bytes = download_blob(
            bucket_name=bucket_name, source_blob_name=source_blob
        )

        artifact_key = "commercial_30s.mp4"
        await tool_context.save_artifact(
            filename=artifact_key,
            artifact=types.Part.from_bytes(
                data=video_bytes, mime_type="video/mp4"
            ),
        )

        tool_context.state["commercial_artifact"] = {
            "artifact_key": artifact_key,
            "gcs_uri": commercial_gcs_uri,
            "metadata": commercial_metadata,
        }

        logging.info(f"Saved commercial artifact '{artifact_key}' to session state")

        return {"status": "ok", "artifact_key": artifact_key}

    except Exception as e:
        logging.error(f"Error saving commercial artifact: {e}")
        return {"status": "failed", "error": str(e)}


def validate_character_consistency(
    reference_image_gcs_uri: str,
    clip_gcs_uri: str,
    frame_position: str,
    tool_context: ToolContext,
) -> dict:
    """Validates character consistency between a reference image and a video clip frame.

    Extracts a frame from the clip and uses Gemini vision to compare the character
    appearance against the reference image, scoring consistency on a 1-10 scale.

    Args:
        reference_image_gcs_uri (str): GCS URI of the character reference image.
        clip_gcs_uri (str): GCS URI of the video clip to validate.
        frame_position (str): Which frame to extract for comparison. Must be "first" or "last".
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Validation result with keys: "status", "score" (1-10), "matches", "mismatches", "suggestion".
    """
    try:
        bucket_name = GCS_BUCKET.replace("gs://", "")

        # Download reference image
        ref_blob = reference_image_gcs_uri.replace(f"gs://{bucket_name}/", "")
        ref_bytes = download_blob(bucket_name=bucket_name, source_blob_name=ref_blob)

        # Download clip and extract frame
        clip_blob = clip_gcs_uri.replace(f"gs://{bucket_name}/", "")
        local_dir = "session_media/av_studio/validation"
        os.makedirs(local_dir, exist_ok=True)
        local_video_path = os.path.join(local_dir, "validation_clip.mp4")

        download_image_from_gcs(
            source_blob_name=clip_blob,
            destination_file_name=local_video_path,
            gcs_bucket=bucket_name,
        )

        cap = cv2.VideoCapture(local_video_path)
        if not cap.isOpened():
            return {"status": "failed", "error": "Could not open video file"}

        if frame_position == "last":
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_number = max(0, total_frames - 1)
        else:
            frame_number = 0

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return {"status": "failed", "error": f"Could not read {frame_position} frame"}

        local_frame_path = os.path.join(local_dir, "validation_frame.png")
        cv2.imwrite(local_frame_path, frame)

        # Read frame bytes
        with open(local_frame_path, "rb") as f:
            frame_bytes = f.read()

        # Use Gemini to compare
        comparison_prompt = """Compare the character in these two images for visual consistency.

Image 1 is the REFERENCE (ground truth). Image 2 is from a generated video clip.

Score the character consistency from 1-10 based on:
- Face similarity (shape, features, expression style)
- Hair (color, style, length)
- Clothing (type, color, fit)
- Build and posture
- Accessories (glasses, jewelry, etc.)

Respond with ONLY a JSON object (no markdown):
{"score": <1-10>, "matches": ["list of consistent elements"], "mismatches": ["list of inconsistent elements"], "suggestion": "one sentence on how to improve consistency if score < 7"}"""

        ref_part = types.Part.from_bytes(data=ref_bytes, mime_type="image/png")
        frame_part = types.Part.from_bytes(data=frame_bytes, mime_type="image/png")

        response = client.models.generate_content(
            model=config.video_analysis_model,
            contents=types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=comparison_prompt),
                    ref_part,
                    frame_part,
                ],
            ),
            config=types.GenerateContentConfig(temperature=0.1),
        )

        # Clean up temp files
        for path in [local_video_path, local_frame_path]:
            if os.path.exists(path):
                os.remove(path)

        if response and response.text:
            import json
            try:
                # Try to parse as JSON
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                result = json.loads(text)
                result["status"] = "ok"
                return result
            except json.JSONDecodeError:
                return {
                    "status": "ok",
                    "score": 5,
                    "matches": [],
                    "mismatches": [],
                    "suggestion": response.text,
                }
        else:
            return {"status": "failed", "error": "Empty response from Gemini"}

    except Exception as e:
        logging.error(f"Error validating character consistency: {e}")
        return {"status": "failed", "error": str(e)}
