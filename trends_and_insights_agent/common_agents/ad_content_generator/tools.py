import os
import uuid
import time

from google import genai
from google.genai import types
from google.genai.types import GenerateVideosConfig
from google.adk import Agent
from google.adk.tools import ToolContext
from google.cloud import storage

from ...utils import download_blob, upload_file_to_gcs, IMAGE_MODEL, VIDEO_MODEL


client = genai.Client()


async def generate_image(
    prompt: str, tool_context: ToolContext, number_of_images: int = 1
):
    """Generates an image based on the prompt.

    Args:
        prompt (str): The prompt to generate the image from.
        tool_context (ToolContext): The tool context.
        number_of_images (int, optional): The number of images to generate. Defaults to 1.

    Returns:
        dict: Status and the location of the image artifact file.

    """
    response = client.models.generate_images(
        model=IMAGE_MODEL,
        prompt=prompt,
        config={"number_of_images": number_of_images},
    )
    if not response.generated_images:
        return {"status": "failed"}
    for image_results in response.generated_images:
        image_bytes = image_results.image.image_bytes
        filename = uuid.uuid4()
        await tool_context.save_artifact(
            f"{filename}.png",
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        )
        # save the file locally for gcs upload
        upload_file_to_gcs(file_path=f"{filename}.png", file_data=image_bytes)
    return {"status": "ok", "filename": f"{filename}.png"}


async def generate_video(
    prompt: str,
    tool_context: "ToolContext",
    number_of_videos: int = 1,
    aspect_ratio: str = "16:9",
    negative_prompt: str = "",
    existing_image_filename: str = "",
):
    """Generates a video based on the prompt.

    Args:
        prompt (str): The prompt to generate the video from.
        tool_context (ToolContext): The tool context.
        number_of_videos (int, optional): The number of videos to generate. Defaults to 1.
        aspect_ratio (str, optional): The aspect ratio of the video. Defaults to "16:9".
        negative_prompt (str, optional): The negative prompt to use. Defaults to "".

    Returns:
        dict: status dict

    Supported aspect ratios are:
        16:9 (landscape) and 9:16 (portrait).
    """
    gen_config = GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        number_of_videos=number_of_videos,
        output_gcs_uri=os.environ["BUCKET"],
        negative_prompt=negative_prompt,
    )
    if existing_image_filename != "":
        gcs_location = f"{os.environ['BUCKET']}/{existing_image_filename}"
        existing_image = types.Image(gcs_uri=gcs_location, mime_type="image/png")
        operation = client.models.generate_videos(
            model=VIDEO_MODEL,
            prompt=prompt,
            image=existing_image,
            config=gen_config,
        )
    else:
        operation = client.models.generate_videos(
            model=VIDEO_MODEL, prompt=prompt, config=gen_config
        )
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(operation)

    if operation.error:
        return {"status": f"failed due to error: {operation.error}"}

    if operation.response:

        for generated_video in operation.result.generated_videos:
            video_uri = generated_video.video.uri
            filename = uuid.uuid4()
            BUCKET = os.getenv("BUCKET")
            video_bytes = download_blob(
                BUCKET.replace("gs://", ""),
                video_uri.replace(BUCKET, "")[1:],  # get rid of slash
            )
            print(f"The location for this video is here: {filename}.mp4")
            await tool_context.save_artifact(
                f"{filename}.mp4",
                types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
            )
        return {"status": "ok", "video_filename": f"{filename}.mp4"}
