import os
import shutil
import logging
from typing import Optional
from markdown_pdf import MarkdownPdf, Section

logging.basicConfig(level=logging.INFO)

from google.genai import types, Client
from google.adk.tools import ToolContext

from .shared_libraries.utils import upload_blob_to_gcs
from .shared_libraries.config import config

# google genai client
client = Client()

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


def analyze_youtube_videos(
    prompt: str,
    youtube_url: str,
) -> Optional[str]:
    """
    Analyzes youtube videos given a prompt and the video's URL

    Args:
        prompt (str): The prompt to use for the analysis.
        youtube_url (str): The url of a YouTube video to analyze.
            The URL should be formatted similarly to: `https://www.youtube.com/watch?v=dmF8oJ5JAVE`, where 'dmF8oJ5JAVE' is the video's ID.
    Returns:
        Results from the youtube video analysis prompt.
    """

    if "youtube.com" not in youtube_url:
        return "Not a valid youtube URL"
    else:
        video = types.Part.from_uri(
            file_uri=youtube_url,
            mime_type="video/*",
        )
        contents = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt), video],
        )
        result = client.models.generate_content(
            model=config.video_analysis_model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )
        if result and result.text is not None:
            return result.text
