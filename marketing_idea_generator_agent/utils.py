import os
from google.cloud import storage

def upload_file_to_gcs(
    file_path: str, 
    file_data: bytes, 
    content_type: str,
    gcs_bucket: str = os.environ.get("BUCKET")
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