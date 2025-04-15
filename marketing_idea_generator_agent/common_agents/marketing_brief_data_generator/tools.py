from pydantic import BaseModel


async def get_marketing_brief(brief_file_path: str, gcs_bucket: str) -> str:
    "Gets marketing brief and uploads it to a GCS bucket."
    from google.cloud import storage

    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(brief_file_path)
    blob.upload_from_filename(brief_file_path)
    return f"gs://{gcs_bucket}/{brief_file_path}"
    

class MarketingCampaignBrief(BaseModel):
    "Data model for marketing campaign brief."
    campaign_name: str
    campaign_objectives: list[str]
    target_audience: str
    media_strategy: list[str]
    timeline: str
    target_countries: list[str]
    performance_metrics: list[str]