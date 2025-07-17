import os
import uuid
import shutil
import logging

from markdown_pdf import MarkdownPdf, Section

from google.adk.tools import ToolContext
from google.genai import types
from google import genai

from ...shared_libraries.utils import upload_blob_to_gcs

logging.basicConfig(level=logging.INFO)
client = genai.Client()


async def generate_research_pdf(
    markdown_string: str,
    tool_context: ToolContext,
) -> dict:
    """Converts a markdown string to PDF.

    Make sure the PDF is formatted correctly with human readable characters.

    Args:
        markdown_string: a string in Markdown format that clearly presents the campaign and trend research.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and `artifact_key` of the generated PDF report.
    """

    # create local dir to save PDF file
    DIR = f"files"
    SUBDIR = f"{DIR}/reports"
    if not os.path.exists(SUBDIR):
        os.makedirs(SUBDIR)

    # filename_prefix = f"{str(uuid.uuid4())[:8]}"
    artifact_key = "final_session_report.pdf"
    local_filepath = f"{SUBDIR}/{artifact_key}"

    pdf = MarkdownPdf(toc_level=0)
    pdf.add_section(Section(f" {markdown_string}\n", toc=False))
    pdf.meta["title"] = "Campaign Research and Creatives"
    pdf.save(local_filepath)

    logging.info(f"\n\n `generate_research_pdf` listdir: {os.listdir('.')}\n\n")

    # open pdf and read bytes for types.Part() object
    with open(local_filepath, "rb") as f:
        document_bytes = f.read()

    document_part = types.Part(
        inline_data=types.Blob(data=document_bytes, mime_type="application/pdf")
    )

    # save artifact
    try:
        version = await tool_context.save_artifact(
            filename=artifact_key, artifact=document_part
        )
        logging.info(f"Saved artifact document '{artifact_key}' as version: {version}")
        gcs_folder = tool_context.state["gcs_folder"]
        artifact_path = os.path.join(gcs_folder, artifact_key)

        # upload_file_to_gcs(
        #     file_path=artifact_path,
        #     file_data=document_bytes,
        #     content_type="application/pdf",
        # )

        upload_blob_to_gcs(
            source_file_name=local_filepath,
            destination_blob_name=artifact_path,
        )
        logging.info(
            f"Saved video artifact '{artifact_key}' to the folder: {gcs_folder}"
        )
    except ValueError as e:
        logging.exception(f"Error saving artifact: {e}. Is ArtifactService configured?")
    except Exception as e:
        # Handle potential storage errors (e.g., GCS permissions)
        logging.exception(f"An unexpected error occurred during artifact save: {e}")

    try:
        shutil.rmtree(SUBDIR)
        logging.info(f"Directory '{SUBDIR}' and its contents removed successfully")
    except FileNotFoundError:
        logging.exception(f"Directory '{SUBDIR}' not found")
    except OSError as e:
        logging.exception(f"Error removing directory '{SUBDIR}': {e}")

    return {"status": "ok", "artifact_key": artifact_key}


# async def get_ad_creative_artifacts(
#     tool_context: ToolContext,
# ) -> dict:
#     """Tool to list available image and video artifacts for the user."""
#     img_creatives = []
#     vid_creatives = []
#     try:
#         available_files = await tool_context.list_artifacts()
#         if not available_files:
#             logging.info("You have no saved artifacts.")
#             return {
#                 "status": "ok",
#                 "message": "You have no saved artifacts.",
#             }
#         else:
#             # Format the list for the user/LLM
#             file_list_str = "\n".join([f"- {fname}" for fname in available_files])
#             for artifact_string in file_list_str:

#                 if artifact_string.endswith(".png"):
#                     img_creatives.append(artifact_string)

#                 if artifact_string.endswith(".mp4"):
#                     vid_creatives.append(artifact_string)

#             return {
#                 "status": "ok",
#                 "img artifact list": img_creatives,
#                 "vid artifact list": vid_creatives,
#             }
#     except ValueError as e:
#         logging.error(
#             f"Error listing Python artifacts: {e}. Is ArtifactService configured?"
#         )
#         return {
#             "status": "error",
#             "error_message": f"Error listing Python artifacts: {e}",
#         }
#     except Exception as e:
#         logging.error(f"An unexpected error occurred during Python artifact list: {e}")
#         return {
#             "status": "error",
#             "error_message": "An unexpected error occurred while listing Python artifacts: {e}",
#         }