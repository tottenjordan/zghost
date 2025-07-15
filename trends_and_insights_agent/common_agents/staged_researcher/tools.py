import os
import shutil
import logging
from markdown_pdf import MarkdownPdf, Section

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import ToolContext


# --- Tools ---
async def save_final_report_artifact(tool_context: ToolContext) -> dict:
    """
    Saves generated PDF report bytes as an artifact.

    Args:
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and the location of the PDF artifact file.
    """
    processed_report = tool_context.state["final_report_with_citations"]

    # create local dir to save PDF file
    try:
        DIR = "files"
        SUBDIR = f"{DIR}/research"
        if not os.path.exists(SUBDIR):
            os.makedirs(SUBDIR)

        filename = "final_report_with_citations.pdf"
        filepath = f"{SUBDIR}/{filename}"

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
            filename=filename, artifact=document_part
        )
        logging.info(
            f"\n\nSaved document: '{filename}' as artifact; version {version}\n\n"
        )

        shutil.rmtree(DIR)
        return {"status": "ok", "filename": filename}
    except Exception as e:
        logging.error(f"Error saving artifact: {e}")
        return {"status": "failed", "error": str(e)}
