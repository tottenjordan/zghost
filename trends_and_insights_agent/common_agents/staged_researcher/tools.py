import os
import shutil
import logging
from markdown_pdf import MarkdownPdf, Section

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import ToolContext

from ...shared_libraries.utils import upload_blob_to_gcs


async def recall_prior_insights(
    brand: str,
    product: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve prior campaign insights from Memory Bank via similarity search.

    Uses Memory Bank's similarity search to find relevant past campaign
    learnings for the given brand/product. Call this during research to
    enrich findings with historical context.

    Args:
        brand: The brand name (e.g. "Tide").
        product: The product name (e.g. "Tide Fabric Softener").
        tool_context: The ADK tool context.

    Returns:
        dict with status and any retrieved prior insights.
    """
    try:
        import vertexai

        agent_engine_id = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
        if not agent_engine_id:
            return {"status": "skipped", "reason": "MEMORY_BANK_AGENT_ENGINE_ID not set", "insights": []}

        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        project_number = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
        location = os.getenv("MEMORY_BANK_LOCATION", "us-central1")

        client = vertexai.Client(project=project, location=location)
        resource_name = f"projects/{project_number}/locations/{location}/reasoningEngines/{agent_engine_id}"

        user_id = tool_context.user_id or "default"
        search_query = (
            f"Campaign insights for {brand} {product}. "
            f"What messaging worked, audience reactions, creative strategies, "
            f"research findings, competitive landscape, trend analysis."
        )

        # Query campaign insights
        results = list(client.agent_engines.memories.retrieve(
            name=resource_name,
            scope={"user_id": user_id, "memory_type": "campaign_insight"},
            similarity_search_params={
                "search_query": search_query,
                "top_k": 5,
            },
        ))

        # Also query skill memories for research patterns that worked
        skill_results = list(client.agent_engines.memories.retrieve(
            name=resource_name,
            scope={"user_id": user_id, "memory_type": "skill_memory", "skill": "research"},
            similarity_search_params={
                "search_query": f"Research techniques and patterns for {brand} {product}",
                "top_k": 5,
            },
        ))
        results.extend(skill_results)

        insights = []
        for result in results:
            fact = getattr(getattr(result, "memory", None), "fact", None)
            if not fact:
                fact = str(result)
            insights.append(fact)

        if insights:
            tool_context.state["prior_campaign_insights"] = "\n- ".join([""] + insights)
            logging.info(f"Retrieved {len(insights)} prior insights for {brand} {product}")
        else:
            tool_context.state["prior_campaign_insights"] = ""
            logging.info(f"No prior insights found for {brand} {product}")

        return {"status": "ok", "num_insights": len(insights), "insights": insights}
    except Exception as e:
        logging.warning(f"Memory Bank recall failed (non-fatal): {e}")
        return {"status": "error", "reason": str(e), "insights": []}

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

        shutil.rmtree(DIR)
        return {
            "status": "ok",
            "artifact_key": artifact_key,
            "message": "Report saved. Use load_artifacts to display it.",
        }
    except Exception as e:
        logging.error(f"Error saving artifact: {e}")
        return {"status": "failed", "error": str(e)}
