import os
import shutil
import logging
from markdown_pdf import MarkdownPdf, Section

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import ToolContext

from ...shared_libraries.utils import upload_blob_to_gcs

# Get the cloud storage bucket from the environment variable
# Note: In Agent Engine, env vars are injected after module import
def get_gcs_bucket():
    bucket = os.environ.get("BUCKET")
    if not bucket:
        raise Exception("BUCKET environment variable not set")
    return bucket

GCS_BUCKET = None  # Will be set at runtime via get_gcs_bucket()


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

        shutil.rmtree(DIR)
        return {
            "status": "ok",
            "gcs_bucket": get_gcs_bucket(),
            "gcs_folder": gcs_folder,
            "artifact_key": artifact_key,
        }
    except Exception as e:
        logging.error(f"Error saving artifact: {e}")
        return {"status": "failed", "error": str(e)}


async def recall_prior_insights(tool_context: ToolContext, query: str) -> dict:
    """Recall prior campaign insights from Memory Bank.

    Use this tool to check if there are relevant insights from previous campaigns
    that could inform the current research. For example: "What visual styles worked
    for Nike before?" or "Which trends were effective for Gen Z audiences?"

    Args:
        tool_context: The tool context.
        query: Natural language query about past campaign insights.

    Returns:
        dict: Retrieved insights from past campaigns.
    """
    try:
        import aiohttp
        from urllib.parse import quote
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"http://localhost:8082/api/memories?user_id=default-user&query={quote(query)}",
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status == 200:
                data = await resp.json()
                memories = data.get("memories", [])
                if memories:
                    return {
                        "status": "found",
                        "insights": memories,
                        "count": len(memories),
                    }
                return {"status": "no_insights", "message": "No prior insights found for this query."}
            return {"status": "error", "message": f"Memory Bank returned status {resp.status}"}
    except Exception as e:
        logging.error(f"Error recalling prior insights: {e}")
        return {"status": "error", "message": str(e)}
