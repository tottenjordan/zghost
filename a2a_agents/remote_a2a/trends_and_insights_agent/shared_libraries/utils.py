import os
import logging

logging.basicConfig(level=logging.INFO)

from google.cloud import storage


def download_image_from_gcs(
    source_blob_name: str,
    destination_file_name: str,
    gcs_bucket: str = os.environ.get("BUCKET", "tmp"),
):
    """
    Downloads a blob (image) from a GCS bucket.

    Args:
        source_blob_name (str): full path to file within bucket e.g., "path/to/your/image.png"
        destination_file_name (str): local path to save file e.g., "local_image.png"
    Returns:
        str: Message indicating local path to file
    """
    storage_client = storage.Client()
    gcs_bucket = gcs_bucket.replace("gs://", "")
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    return f"Downloaded gcs object {source_blob_name} from {gcs_bucket} to (local) {destination_file_name}."


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
        file_data (str): The file bytes to upload.
        content_type (str): The file's mime type.
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


def upload_blob_to_gcs(
    source_file_name: str,
    destination_blob_name: str,
    gcs_bucket: str = os.environ.get("BUCKET", "tmp"),
) -> str:
    """
    Uploads a blob to a GCS bucket.
    Args:
        source_file_name (str): The path to the file to upload.
        destination_blob_name (str): The desired folder path in gcs
        gcs_bucket (str): The name of the GCS bucket.
    Returns:
        str: The GCS URI of the uploaded file.
    """
    # bucket_name = "your-bucket-name" (no 'gs://')
    # source_file_name = "local/path/to/file" (file to upload)
    # destination_blob_name = "folder/paths-to/storage-object-name"
    storage_client = storage.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    gcs_bucket = gcs_bucket.replace("gs://", "")
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    return f"File {source_file_name} uploaded to {destination_blob_name}."
