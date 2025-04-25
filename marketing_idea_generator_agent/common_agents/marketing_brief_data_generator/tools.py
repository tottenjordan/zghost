from pydantic import BaseModel


class MarketingCampaignBrief(BaseModel):
    "Data model for marketing campaign brief."

    campaign_name: str
    target_product: str
    target_audience: str
    target_regions: list[str]
    campaign_objectives: list[str]
    media_strategy: list[str]
    timeline: str
    performance_metrics: list[str]
    key_insights: list[str]
    campaign_brief_highlights: list[str]

async def get_marketing_brief(brief_file_path: str, gcs_bucket: str) -> str:
    "Gets marketing brief and uploads it to a GCS bucket."
    from google.cloud import storage

    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(brief_file_path)
    blob.upload_from_filename(brief_file_path)
    return f"gs://{gcs_bucket}/„{brief_file_path}"
