from google.adk import Agent
from google.adk.tools import ToolContext

from google.genai import types
from google.genai.types import GenerateVideosConfig
from google.genai import types
import time
import os
import uuid
from google.cloud import storage

from google import genai

client = genai.Client()


def generate_image(prompt: str, tool_context: ToolContext, number_of_images: int = 1):
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
        # save the file locally for gcs upload
        upload_file_to_gcs(file_path=f"{filename}.png", file_data=image_bytes)
    return {"status": "ok", "filename": f"{filename}.png"}


def upload_file_to_gcs(
    file_path: str, file_data: bytes, gcs_bucket: str = os.environ.get("BUCKET")
):
    """
    Uploads a file to a GCS bucket.
    Args:
        file_path (str): The path to the file to upload.
        gcs_bucket (str): The name of the GCS bucket.
    Returns:
        str: The GCS URI of the uploaded file.
    """
    gcs_bucket = gcs_bucket.replace("gs://", "")
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(os.path.basename(file_path))
    blob.upload_from_string(file_data, content_type="image/png")
    return f"gs://{gcs_bucket}/{os.path.basename(file_path)}"


from google.cloud import storage


def download_blob(bucket_name, source_blob_name):
    """Downloads a blob from the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"

    # The ID of your GCS object
    # source_blob_name = "storage-object-name"

    # The path to which the file should be downloaded
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    return blob.download_as_bytes()


def generate_video(
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
        16:9 (landscape) and 9:16 (portrait) are supported.
    """
    gen_config = GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        number_of_videos=number_of_videos,
        output_gcs_uri=os.environ.get("BUCKET"),
        negative_prompt=negative_prompt,
    )
    if existing_image_filename is not "":
        gcs_location = f"{os.environ.get('BUCKET')}/{existing_image_filename}"
        existing_image = types.Image(gcs_uri=gcs_location, mime_type="image/png")
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=prompt,
            image=existing_image,
            config=gen_config,
        )
    else:
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001", prompt=prompt, config=gen_config
        )
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(operation)

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
            tool_context.save_artifact(
                f"{filename}.mp4",
                types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
            )
        return {"status": "ok"}
