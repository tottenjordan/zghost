import os
import logging

logging.basicConfig(level=logging.INFO)

from google.cloud import storage
from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.genai import types


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


def brief_callback_function(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    This sets default values for:
        *   campaign_brief
        *   trends
        *   insights
    """

    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()
    logging.info(f"\n[Callback] Entering agent: {agent_name} (Inv: {invocation_id})")
    logging.info(f"[Callback] Current State: {current_state}")

    # Check the condition in session state dictionary
    marketing_brief = callback_context.state.get("campaign_brief")
    trends = callback_context.state.get("trends")
    insights = callback_context.state.get("insights")
    product_insights = callback_context.state.get("product_insights")
    return_content = None  # placeholder for optional returned parts
    if marketing_brief is None:
        return_content = "campaign_brief"
        callback_context.state["campaign_brief"] = {
            "campaign_brief": "not yet populated"
        }

    if trends is None:
        callback_context.state["trends"] = {"trends": []}
        if return_content is None:
            return_content = "trends"
        else:
            return_content += ", trends"

    if insights is None:
        callback_context.state["insights"] = {"insights": []}
        if return_content is None:
            return_content = "insights"
        else:
            return_content += ", insights"

    if product_insights is None:
        callback_context.state["product_insights"] = {"product_insights": []}
        if return_content is None:
            return_content = "product_insights"
        else:
            return_content += ", product_insights"

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
