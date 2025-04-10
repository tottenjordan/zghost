from google.adk import Agent
from google.adk.tools import load_artifacts
from google.adk.tools import ToolContext
from google.genai import Client
from google.genai import types
from google.genai.types import GenerateVideosConfig, Image
import time
import os

# Only Vertex AI supports image generation for now.
client = Client()


def generate_image(prompt: str, tool_context: "ToolContext"):
    """Generates an image based on the prompt."""
    response = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config={"number_of_images": 1},
    )
    if not response.generated_images:
        return {"status": "failed"}
    image_bytes = response.generated_images[0].image.image_bytes
    tool_context.save_artifact(
        "image.png",
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
    )
    return {"status": "ok", "filename": "image.png"}


def generate_video(prompt: str, tool_context: "ToolContext"):
    """Generates an image based on the prompt."""

    operation = client.models.generate_videos(
        model="veo-2.0-generate-001",
        prompt=prompt,
        config=GenerateVideosConfig(
            aspect_ratio="16:9",
            output_gcs_uri=os.environ.get("BUCKET"),
        ),
    )
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(operation)

    if operation.response:
        video_uri = operation.result.generated_videos[0].video.uri
        tool_context.save_artifact(
            "video.mp4",
            types.Part.from_uri(file_uri=video_uri, mime_type="video/mp4"),
        )
        return {"status": "ok", "filename": "video.png"}
