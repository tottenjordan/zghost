import os
import uuid
from typing import Union, Optional

from google.adk.tools import ToolContext
from google import genai
from google.genai import types

client = genai.Client()


def generate_brief_pdf(
    prompt: str,
    tool_context: ToolContext,
) -> dict:
    """Converts the campaign brief to PDF and saves it to Google Cloud Storage

    Make sure the PDF is formatted correctly with human readable characters.
    
    Args:
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and the location of the PDF.
    """
    print(f"prompt in `generate_brief_pdf`: {prompt}")

    filename = uuid.uuid4()
    # response = client.models.generate_content(
    #     model="gemini-1.5-flash-002", # "gemini-2.0-flash-001"
    #     contents=prompt,
    #     # contents="Generate the updated campaign brief in Markdown format",
    # )
    # if not response.text:
    #     return {"status": "failed"}
    
    # markdown_string = response.text
    markdown_string = prompt
    markdown_bytes = markdown_string.encode('utf-8')

    pdf_artifact =types.Part(
        inline_data=types.Blob(
            data=markdown_bytes,
            mime_type="application/pdf"
        )
    )
    
    tool_context.save_artifact(
        filename=f"{filename}.pdf",
        # artifact= types.Part.from_bytes(data=markdown_bytes, mime_type="application/pdf"),
        artifact=pdf_artifact,
    )

    # save the file locally for gcs upload
    upload_pdf_to_gcs(file_path=f"{filename}.pdf", file_data=markdown_bytes)
    return {"status": "ok", "filename": f"{filename}.pdf"}


def upload_pdf_to_gcs(
    file_path: str, file_data: bytes, gcs_bucket: str = os.environ.get("BUCKET")
):
    """ Uploads a file to a GCS bucket.
    
    Args:
        file_path (str): The path to the file to upload.
        gcs_bucket (str): The name of the GCS bucket.
    Returns:
        str: The GCS URI of the uploaded file.
    """
    from google.cloud import storage
    gcs_bucket = gcs_bucket.replace("gs://", "")
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(os.path.basename(file_path))
    blob.upload_from_string(file_data, content_type="application/pdf")
    return f"gs://{gcs_bucket}/{os.path.basename(file_path)}"