import os
import shutil
import logging
from markdown_pdf import MarkdownPdf, Section

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import ToolContext

from ...shared_libraries.utils import upload_blob_to_gcs

# Get the cloud storage bucket from the environment variable
try:
    GCS_BUCKET = os.environ["BUCKET"]
except KeyError:
    raise Exception("BUCKET environment variable not set")


# --- Tools ---
async def save_draft_report_artifact(tool_context: ToolContext) -> dict:
    """
    Saves generated PDF report bytes as an artifact.

    Args:
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and the location of the generated PDF artifact.
    """
    processed_report = tool_context.state["final_report_with_citations"]

    # create local dir to save PDF file
    try:
        DIR = "files"
        SUBDIR = f"{DIR}/research"
        if not os.path.exists(SUBDIR):
            os.makedirs(SUBDIR)

        artifact_key = "draft_research_report_with_citations.pdf"
        filepath = f"{SUBDIR}/{artifact_key}"

        pdf = MarkdownPdf(toc_level=4)
        pdf.add_section(Section(f" {processed_report}\n"))
        pdf.meta["title"] = "[Draft] Trend & Campaign Research Report"
        pdf.save(filepath)

        # open pdf and read bytes for types.Part() object
        with open(filepath, "rb") as f:
            document_bytes = f.read()

        document_part = types.Part(
            inline_data=types.Blob(data=document_bytes, mime_type="application/pdf")
        )
        version = await tool_context.save_artifact(
            filename=artifact_key, artifact=document_part
        )
        gcs_folder = tool_context.state["gcs_folder"]

        upload_blob_to_gcs(
            source_file_name=filepath,
            destination_blob_name=os.path.join(gcs_folder, artifact_key),
        )
        logging.info(
            f"\n\nSaved artifact doc '{artifact_key}', version {version}, to folder '{gcs_folder}' \n\n"
        )

        # Add PDF artifact to state
        pdf_artifacts = tool_context.state.get("pdf_artifact_keys", {"pdf_artifact_keys": []})
        pdf_artifacts["pdf_artifact_keys"].append({
            "artifact_key": artifact_key,
            "version": version
        })
        tool_context.state["pdf_artifact_keys"] = pdf_artifacts
        
        shutil.rmtree(DIR)
        return {
            "status": "ok",
            "gcs_bucket": GCS_BUCKET,
            "gcs_folder": gcs_folder,
            "artifact_key": artifact_key,
        }
    except Exception as e:
        logging.error(f"Error saving artifact: {e}")
        return {"status": "failed", "error": str(e)}
