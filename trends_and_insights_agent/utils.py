import os
import logging

logging.basicConfig(level=logging.INFO)

from google.cloud import storage
from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.genai import types


MODEL = "gemini-2.0-flash-001"  # "gemini-2.0-flash-001" | "gemini-2.5-flash" | "gemini-2.5-pro-preview-06-05"
IMAGE_MODEL = "imagen-4.0-fast-generate-preview-06-06"  # "imagen-4.0-ultra-generate-preview-06-06" "imagen-4.0-generate-preview-06-06"
VIDEO_MODEL = "veo-2.0-generate-001"  # veo-3.0-generate-preview


def upload_file_to_gcs(
    file_path: str,
    file_data: bytes,
    content_type: str,
    gcs_bucket: str = os.environ.get("BUCKET"),
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
    file_path: str, file_data: bytes, gcs_bucket: str = os.environ["BUCKET"]
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


def campaign_callback_function(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    This sets default values for:
        *   campaign_guide
        *   search_trends
        *   yt_trends
        *   insights
        *   target_search_trends
        *   target_yt_trends
    """

    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()
    # logging.info(f"\n[Callback] Entering agent: {agent_name} (Inv: {invocation_id})")
    # logging.info(f"\n[Callback] Current State: {current_state}")

    # Check the condition in session state dictionary
    yt_trends = callback_context.state.get("yt_trends")
    search_trends = callback_context.state.get("search_trends")
    target_yt_trends = callback_context.state.get("target_yt_trends")
    target_search_trends = callback_context.state.get("target_search_trends")
    insights = callback_context.state.get("insights")
    campaign_guide = callback_context.state.get("campaign_guide")

    return_content = None  # placeholder for optional returned parts
    if campaign_guide is None:
        return_content = "campaign_guide"
        callback_context.state["campaign_guide"] = {
            "campaign_guide": "not yet populated"
        }

    if search_trends is None:
        callback_context.state["search_trends"] = {"search_trends": []}
        if return_content is None:
            return_content = "search_trends"
        else:
            return_content += ", search_trends"

    if yt_trends is None:
        callback_context.state["yt_trends"] = {"yt_trends": []}
        if return_content is None:
            return_content = "yt_trends"
        else:
            return_content += ", yt_trends"

    if insights is None:
        callback_context.state["insights"] = {"insights": []}
        if return_content is None:
            return_content = "insights"
        else:
            return_content += ", insights"

    if target_search_trends is None:
        callback_context.state["target_search_trends"] = {"target_search_trends": []}
        if return_content is None:
            return_content = "target_search_trends"
        else:
            return_content += ", target_search_trends"

    if target_yt_trends is None:
        callback_context.state["target_yt_trends"] = {"target_yt_trends": []}
        if return_content is None:
            return_content = "target_yt_trends"
        else:
            return_content += ", target_yt_trends"

    if return_content is not None:
        return types.Content(
            parts=[
                types.Part(
                    text=f"Agent {agent_name} setting default values for state variables: {return_content}."
                )
            ],
            role="model",  # Assign model role to the overriding response
        )

    else:
        return None
