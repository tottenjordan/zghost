from google.adk import Agent
from google.adk.tools import load_artifacts
from google.adk.tools import ToolContext
from google.genai import Client
from google.genai import types
from google.genai.types import GenerateVideosConfig, Image
import time
import os
import uuid
from google.cloud import storage


# Only Vertex AI supports image generation for now.
client = Client()


def generate_image(prompt: str, tool_context: "ToolContext", number_of_images: int = 1):
    """Generates an image based on the prompt.
    Args:
        prompt (str): The prompt to generate the image from.
        tool_context (ToolContext): The tool context.
        number_of_images (int, optional): The number of images to generate. Defaults to 1.

    Returns:
        dict: Status and the location of the image.

    """
    response = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config={"number_of_images": number_of_images},
    )
    if not response.generated_images:
        return {"status": "failed"}
    for image_results in response.generated_images:
        image_bytes = image_results.image.image_bytes
        filename = uuid.uuid4()
        tool_context.save_artifact(
            f"{filename}.png",
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        )
    return {"status": "ok", "filename": f"{filename}.png"}


def generate_video(
    prompt: str,
    tool_context: "ToolContext",
    number_of_videos: int = 1,
    aspect_ratio: str = "16:9",
    negative_prompt: str = "",
) -> str:
    """Generates an image based on the prompt.
    Args:
        prompt (str): The prompt to generate the video from.
        tool_context (ToolContext): The tool context.
        number_of_videos (int, optional): The number of videos to generate. Defaults to 1.
        aspect_ratio (str, optional): The aspect ratio of the video. Defaults to "16:9".
        negative_prompt (str, optional): The negative prompt to use. Defaults to "".

    Returns:
        str: The location of the video.

    Supported aspect ratios are:
        16:9 (landscape) and 9:16 (portrait) are supported.
    """

    operation = client.models.generate_videos(
        model="veo-2.0-generate-001",
        prompt=prompt,
        config=GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            number_of_videos=number_of_videos,
            output_gcs_uri=os.environ.get("BUCKET"),
            negative_prompt=negative_prompt,
        ),
    )
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(operation)

    if operation.response:

        for generated_video in operation.result.generated_videos:
            video_uri = generated_video.video.uri
            video_url = video_uri.replace("gs://", "https://storage.googleapis.com/")
            filename = uuid.uuid4()
            print(f"The location for this video is here: {video_url}")
            tool_context.save_artifact(
                f"{filename}.mp4",
                types.Part.from_uri(file_uri=video_url, mime_type="video/mp4"),
            )
        return f"The location for this video is here: {video_url}"
