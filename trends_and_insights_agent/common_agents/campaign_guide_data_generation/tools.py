from pydantic import BaseModel


# get_marketing_brief
async def get_marketing_guide(guide_file_path: str, gcs_bucket: str) -> str:
    "Gets marketing brieguidef and uploads it to a GCS bucket."
    from google.cloud import storage

    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(guide_file_path)
    blob.upload_from_filename(guide_file_path)
    return f"gs://{gcs_bucket}/„{guide_file_path}"
