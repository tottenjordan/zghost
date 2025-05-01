from pydantic import BaseModel


# MarketingCampaignBrief
class MarketingCampaignGuide(BaseModel):
    "Data model for marketing campaign guide."

    campaign_name: str
    brand: str
    target_product: str
    target_audience: str
    target_regions: list[str]
    campaign_objectives: list[str]
    media_strategy: list[str]
    key_insights: list[str]
    campaign_highlights: list[str]


# get_marketing_brief
async def get_marketing_guide(guide_file_path: str, gcs_bucket: str) -> str:
    "Gets marketing brieguidef and uploads it to a GCS bucket."
    from google.cloud import storage

    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(guide_file_path)
    blob.upload_from_filename(guide_file_path)
    return f"gs://{gcs_bucket}/„{guide_file_path}"
