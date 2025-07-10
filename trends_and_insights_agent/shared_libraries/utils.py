import os
import logging

logging.basicConfig(level=logging.INFO)

from google.cloud import storage


MODEL = "gemini-2.5-flash"  # "gemini-2.0-flash-001" | "gemini-2.0-flash-lite-001" | "gemini-2.5-flash" | "gemini-2.5-pro-preview-06-05"
IMAGE_MODEL = "imagen-4.0-fast-generate-preview-06-06"  # "imagen-4.0-ultra-generate-preview-06-06" "imagen-4.0-generate-preview-06-06"
VIDEO_MODEL = (
    "veo-3.0-generate-preview"  # "veo-3.0-generate-preview" | veo-3.0-generate-preview
)


def download_blob(bucket_name, source_blob_name):
    """
    Downloads a blob from the bucket.
    Args:
        bucket_name (str): The ID of your GCS bucket
        source_blob_name (str): The ID of your GCS object
    Returns:
        Blob content as bytes.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    return blob.download_as_bytes()


def upload_file_to_gcs(
    file_path: str,
    file_data: bytes,
    content_type: str = "image/png",
    gcs_bucket: str = os.environ.get("BUCKET", "tmp"),
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
    blob.upload_from_string(file_data, content_type=content_type)
    return f"gs://{gcs_bucket}/{os.path.basename(file_path)}"
