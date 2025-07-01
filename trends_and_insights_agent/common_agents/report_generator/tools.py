import os
import uuid
import shutil
import logging

from markdown_pdf import MarkdownPdf, Section

from google.adk.tools import ToolContext
from google.genai import types
from google import genai

logging.basicConfig(level=logging.INFO)
client = genai.Client()


async def generate_research_pdf(
    markdown_string: str,
    tool_context: ToolContext,
) -> dict:
    """Converts a markdown string to PDF.

    Make sure the PDF is formatted correctly with human readable characters.

    Args:
        markdown_string: a string in Markdown format that clearly presents the session state: `campaign_guide`, `search_trends`, `yt_trends`, and `insights`
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and the location of the PDF.
    """
    # logging.info(f"markdown_string in `generate_research_pdf`: {markdown_string}")

    # TODO: add these state vairables to report
    # campaign_research_markdown = tool_context.state['final_ca_report_with_citations']
    # gs_research_markdown = tool_context.state['final_gs_report_with_citations']

    # create local dir to save PDF file
    DIR = f"files/research"
    if not os.path.exists(DIR):
        os.makedirs(DIR)

    filename = uuid.uuid4()
    filename = str(filename)[:8]
    filepath = f"{DIR}/report_{filename}.pdf"

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

    # save artifact
    try:
        version = await tool_context.save_artifact(
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

    try:
        shutil.rmtree(DIR)
        logging.info(f"Directory '{DIR}' and its contents removed successfully")
    except FileNotFoundError:
        logging.exception(f"Directory '{DIR}' not found")
    except OSError as e:
        logging.exception(f"Error removing directory '{DIR}': {e}")

    return {"status": "ok", "filename": artifact_filename}
