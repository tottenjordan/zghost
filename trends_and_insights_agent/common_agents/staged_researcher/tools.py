import os
import shutil
import logging
from markdown_pdf import MarkdownPdf, Section

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import ToolContext

from ...shared_libraries.utils import upload_file_to_gcs, upload_blob_to_gcs


# --- Tools ---
async def save_final_report_artifact(tool_context: ToolContext) -> dict:
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

        artifact_key = "research_report_with_citations.pdf"
        filepath = f"{SUBDIR}/{artifact_key}"

        pdf = MarkdownPdf(toc_level=0)
        pdf.add_section(Section(f" {processed_report}\n", toc=False))
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
        
        # artifact_path = os.path.join(gcs_folder, artifact_key)
        # upload_file_to_gcs(
        #     file_path=artifact_path,
        #     file_data=document_bytes,
        #     content_type="application/pdf",
        # )

        upload_blob_to_gcs(
            source_file_name=filepath,
            destination_blob_name=os.path.join(gcs_folder, artifact_key),
        )
        logging.info(
            f"\n\nSaved artifact doc '{artifact_key}', version {version}, to folder '{gcs_folder}' \n\n"
        )

        shutil.rmtree(DIR)
        return {"status": "ok", "artifact_key": artifact_key}
    except Exception as e:
        logging.error(f"Error saving artifact: {e}")
        return {"status": "failed", "error": str(e)}
