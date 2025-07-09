import os
import uuid
import time
import subprocess
import tempfile
from typing import List

import logging
from google import genai
from google.genai import types
from google.genai.types import GenerateVideosConfig
from google.adk.tools import ToolContext

from ...utils import download_blob, upload_file_to_gcs
from ...shared_libraries.config import config

client = genai.Client()


async def generate_image(
    prompt: str,
    tool_context: ToolContext,
    concept_name: str,
    number_of_images: int = 1,
) -> dict:
    f"""Generates an image based on the prompt for {config.image_gen_model}

    Args:
        prompt (str): The prompt to generate the image from.
        tool_context (ToolContext): The tool context.
        concept_name (str, optional): The name of the concept.
        number_of_images (int, optional): The number of images to generate. Defaults to 1.

    Returns:
        dict: Status and the location of the image artifact file.

    """
    response = client.models.generate_images(
        model=config.image_gen_model,
        prompt=prompt,
        config={"number_of_images": number_of_images},
    )
    if not response.generated_images:
        return {"status": "failed"}

    # Create output filename
    if concept_name:
        concept_name = concept_name.replace(" ", "_")
        filename_prefix = f"{concept_name}"
    else:
        filename_prefix = f"{uuid.uuid4()}"

    for index, image_results in enumerate(response.generated_images):
        if image_results.image is not None:
            if image_results.image.image_bytes is not None:
                image_bytes = image_results.image.image_bytes
                filename = f"{filename_prefix}_{index}.png"
                await tool_context.save_artifact(
                    filename,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                )
                # new_entry = {filename: prompt}
                # tool_context.state["artifact_keys"]["image_creatives"].update(new_entry)

                # save the file locally for gcs upload
                upload_file_to_gcs(file_path=f"{filename}", file_data=image_bytes)

    return {"status": "ok", "filename": f"{filename}"}


async def generate_video(
    prompt: str,
    tool_context: ToolContext,
    number_of_videos: int = 1,
    # aspect_ratio: str = "16:9",
    negative_prompt: str = "",
    existing_image_filename: str = "",
):
    f"""Generates a video based on the prompt for {config.video_gen_model}.

    Args:
        prompt (str): The prompt to generate the video from.
        tool_context (ToolContext): The tool context.
        number_of_videos (int, optional): The number of videos to generate. Defaults to 1.
        negative_prompt (str, optional): The negative prompt to use. Defaults to "".

    Returns:
        dict: status dict


    """
    gen_config = GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=number_of_videos,
        output_gcs_uri=os.environ["BUCKET"],
        negative_prompt=negative_prompt,
    )
    if existing_image_filename != "":
        gcs_location = f"{os.environ['BUCKET']}/{existing_image_filename}"
        existing_image = types.Image(gcs_uri=gcs_location, mime_type="image/png")
        operation = client.models.generate_videos(
            model=config.video_gen_model,
            prompt=prompt,
            image=existing_image,
            config=gen_config,
        )
    else:
        operation = client.models.generate_videos(
            model=config.video_gen_model, prompt=prompt, config=gen_config
        )
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(operation)

    if operation.error:
        return {"status": f"failed due to error: {operation.error}"}

    if operation.response:
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
                    filename = uuid.uuid4()
                    BUCKET = os.getenv("BUCKET")
                    if BUCKET is not None:
                        video_bytes = download_blob(
                            BUCKET.replace("gs://", ""),
                            video_uri.replace(BUCKET, "")[1:],  # get rid of slash
                        )
                        print(f"The location for this video is here: {filename}.mp4")
                        await tool_context.save_artifact(
                            f"{filename}.mp4",
                            types.Part.from_bytes(
                                data=video_bytes, mime_type="video/mp4"
                            ),
                        )
                    return {"status": "ok", "video_filename": f"{filename}.mp4"}


async def concatenate_videos(
    video_filenames: List[str],
    tool_context: ToolContext,
    concept_name: str,
):
    """Concatenates multiple videos into a single longer video for a concept.

    Args:
        video_filenames (List[str]): List of video filenames from tool_context artifacts.
        tool_context (ToolContext): The tool context.
        concept_name (str, optional): The name of the concept.

    Returns:
        dict: Status and the location of the concatenated video file.
    """
    if not video_filenames:
        return {"status": "failed", "error": "No video filenames provided"}

    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Load videos from artifacts and save locally
            local_video_paths = []
            for idx, video_filename in enumerate(video_filenames):
                # Load artifact
                video_part = await tool_context.load_artifact(video_filename)
                if not video_part:
                    return {
                        "status": "failed",
                        "error": f"Could not load artifact: {video_filename}",
                    }
                if not video_part.inline_data:
                    return {
                        "status": "failed",
                        "error": f"Could not load artifact inline_data: {video_filename}",
                    }
                if not video_part.inline_data.data:
                    return {
                        "status": "failed",
                        "error": f"Could not load artifact inline_data.data: {video_filename}",
                    }

                # Extract bytes from the Part object
                video_bytes = video_part.inline_data.data

                # Save locally for ffmpeg processing
                local_path = os.path.join(temp_dir, f"video_{idx}.mp4")
                with open(local_path, "wb") as f:
                    f.write(video_bytes)
                local_video_paths.append(local_path)

            # Create output filename
            if concept_name:
                output_filename = f"{concept_name}.mp4"
            else:
                output_filename = f"{uuid.uuid4()}.mp4"

            output_path = os.path.join(temp_dir, output_filename)

            if len(local_video_paths) == 1:
                # If only one video, just copy it
                subprocess.run(["cp", local_video_paths[0], output_path], check=True)
            else:
                # Create ffmpeg filter complex for concatenation with transitions
                # Simple concatenation without transitions
                concat_file = os.path.join(temp_dir, "concat_list.txt")
                with open(concat_file, "w") as f:
                    for video_path in local_video_paths:
                        f.write(f"file '{video_path}'\n")

                subprocess.run(
                    [
                        "ffmpeg",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        concat_file,
                        "-c",
                        "copy",
                        output_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

            # Read the output video
            with open(output_path, "rb") as f:
                video_bytes = f.read()

            # Save as artifact
            await tool_context.save_artifact(
                output_filename,
                types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
            )

            # Also upload to GCS for persistence
            gcs_uri = upload_file_to_gcs(
                file_path=output_filename,
                file_data=video_bytes,
                content_type="video/mp4",
            )
            new_entry = {output_filename: gcs_uri}
            tool_context.state["artifact_keys"]["video_creatives"].update(new_entry)

            return {
                "status": "ok",
                "video_filename": output_filename,
                "gcs_uri": gcs_uri,
                "num_videos_concatenated": len(video_filenames),
            }

    except subprocess.CalledProcessError as e:
        return {
            "status": "failed",
            "error": f"FFmpeg error: {e.stderr if hasattr(e, 'stderr') else str(e)}",
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}
