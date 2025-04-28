import os
import uuid
import base64
import logging

logging.basicConfig(level=logging.INFO)
from typing import Union, Optional
from markdown_pdf import MarkdownPdf, Section

from google.adk.tools import ToolContext
from google.genai import types
from google import genai

client = genai.Client()

from ...utils import upload_file_to_gcs


def generate_brief_pdf(
    markdown_string: str,
    tool_context: ToolContext,
) -> dict:
    """Converts a markdown string to PDF.

    Make sure the PDF is formatted correctly with human readable characters.

    Args:
        markdown_string: a string in Markdown format that clearly presents the session state: {campaign_brief}, {trends}, and {insights}
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and the location of the PDF.
    """
    logging.info(f"markdown_string in `generate_brief_pdf`: {markdown_string}")

    filename = uuid.uuid4()
    filepath = f"{filename}.pdf"

    pdf = MarkdownPdf(toc_level=0)
    pdf.add_section(Section(f" {markdown_string}\n", toc=False))
    pdf.meta["title"] = "Campaign Research Trends and Insights"
    pdf.save(filepath)

    # open pdf and read bytes for types.Part() object
    with open(filepath, "rb") as f:
        document_bytes = f.read()

    document_part = types.Part(
        inline_data=types.Blob(data=document_bytes, mime_type="application/pdf")
    )
    artifact_filename = "generated_report.pdf"

    try:
        version = tool_context.save_artifact(
            filename=artifact_filename, artifact=document_part
        )
        logging.info(
            f"Saved document reference '{filepath}' as artifact version {version}"
        )
    except ValueError as e:
        logging.exception(f"Error saving artifact: {e}. Is ArtifactService configured?")
    except Exception as e:
        # Handle potential storage errors (e.g., GCS permissions)
        logging.exception(f"An unexpected error occurred during artifact save: {e}")

    # upload local file to GCS
    # gcs_blob_path = upload_filename_blob_to_gcs(source_file_path=filepath)
    gcs_blob_path = upload_file_to_gcs(
        file_path=filepath, file_data=document_bytes, content_type="application/pdf"
    )
    logging.info(f"Saved PDF to: {gcs_blob_path}")

    return {"status": "ok", "filename": filepath}


# def upload_pdf_to_gcs(
#     file_path: str, file_data: bytes, gcs_bucket: str = os.environ.get("BUCKET")
# ):
#     """Uploads a file to a GCS bucket.

#     Args:
#         file_path (str): The path to the file to upload.
#         gcs_bucket (str): The name of the GCS bucket.
#     Returns:
#         str: The GCS URI of the uploaded file.
#     """
#     from google.cloud import storage

#     gcs_bucket = gcs_bucket.replace("gs://", "")
#     storage_client = storage.Client()
#     bucket = storage_client.bucket(gcs_bucket)
#     blob = bucket.blob(os.path.basename(file_path))
#     blob.upload_from_string(file_data, content_type="application/pdf")
#     return f"gs://{gcs_bucket}/{os.path.basename(file_path)}"


# testing save via filename vs bytes
def upload_filename_blob_to_gcs(
    source_file_path: str,
    gcs_bucket: str = os.environ.get("BUCKET"),
):
    """
    Uploads a file to the bucket.
    """
    from google.cloud import storage

    storage_client = storage.Client()
    gcs_bucket = gcs_bucket.replace("gs://", "")
    destination_blob_name = f"gs://{gcs_bucket}/{os.path.basename(source_file_path)}"

    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"File {source_file_path} uploaded to {destination_blob_name}.")
    return destination_blob_name
