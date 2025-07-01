import logging

logging.basicConfig(level=logging.INFO)

from google import genai
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents import Agent, LlmAgent, SequentialAgent, ParallelAgent

from ...common_agents.yt_researcher.agent import (
    yt_research_pipeline,
)  # yt_researcher_agent
from ...common_agents.gs_researcher.agent import (
    gs_research_pipeline,
)  # gs_researcher_agent
from ...common_agents.campaign_researcher.agent import (
    campaign_research_pipeline,
)  # campaign_researcher_agent
from ...shared_libraries import callbacks, schema_types
from ...utils import MODEL


# --- Callbacks ---
async def process_report_htmls(
    # artifact_key: str,
    # tool_context: ToolContext
    callback_context: CallbackContext,
) -> dict[str, str]:
    """
    Processes markdown repots from session state and saves as an HTML artifact.

    Args:
        callback_context: The execution context for the tool, automatically provided
            by the ADK framework. It is used here to access the `session.state`.

    Returns:
        None
    """

    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    # current_state = callback_context.state.to_dict()

    campaign_report_markdown = callback_context.state["ca_final_cited_report"]
    search_report_markdown = callback_context.state["gs_final_cited_report"]
    youtube_report_markdown = callback_context.state["yt_final_cited_report"]

    logging.info(f"\n\n ## JT DEBUGGING - BEGIN ## \n\n")
    logging.info(f"\n\n agent_name: {agent_name} \n\n")
    logging.info(f"\n\n{campaign_report_markdown}\n\n")
    logging.info(f"\n\n{search_report_markdown}\n\n")
    logging.info(f"\n\n{youtube_report_markdown}\n\n")
    logging.info(f"\n\n ## JT DEBUGGING - END ## \n\n")

    return None


# --- 2. Create the ParallelAgent (Runs researchers concurrently) ---
# This agent orchestrates the concurrent execution of the researchers.
# It finishes once all researchers have completed and stored their results in state.
stage_1_parallel_research_agent = ParallelAgent(
    name="stage_1_parallel_research_agent",
    sub_agents=[yt_research_pipeline, gs_research_pipeline, campaign_research_pipeline],
    description="Runs multiple research SequentialAgents in parallel to gather information.",
)

# --- 3. Define the Merger Agent (Runs *after* the parallel agents) ---
# This agent takes the results stored in the session state by the parallel agents
# and synthesizes them into a single, structured response with attributions.
stage_1_merger_agent = LlmAgent(
    name="stage_1_merger_agent",
    model=MODEL,
    description="Combines research findings from parallel agents into a structured, cited report, strictly grounded on provided inputs.",
    instruction="""You are an AI Assistant responsible for combining research findings into a structured report.

    Merge each cited report here:

    ---
    **Output Format:**

    ## Summary of Trends & Insights
    
    ### Campaign Findings

    `{ca_final_cited_report}`
    
    ### Search Trend Findings

    `{gs_final_cited_report}`
    
    ### YouTube Trend Findings

    `{yt_final_cited_report}`
    
    ---
    Output *only* the structured report following this format. 
    Do not include introductory or concluding phrases outside this structure, and strictly adhere to using only the provided input summary content.
    Upon completion, transfer to the `root_agent`.
    """,
    before_agent_callback=process_report_htmls,
    # No output_key needed here, as its direct response is the final output of the sequence
)

# --- 4. Create the SequentialAgent (Orchestrates the overall flow) ---
# This is the main agent that will be run. It first executes the ParallelAgent
# to populate the state, and then executes the MergerAgent to produce the final output.
stage_1_research_merger = SequentialAgent(
    name="stage_1_research_merger",
    # Run parallel research first, then merge
    sub_agents=[stage_1_parallel_research_agent, stage_1_merger_agent],
    description="Coordinates parallel research and synthesizes the results.",
)


# try:
#     # here
#     campaign_report_markdown = tool_context.state["ca_final_cited_report"]
#     search_report_markdown = tool_context.state["gs_final_cited_report"]
#     youtube_report_markdown = tool_context.state["yt_final_cited_report"]

#     logging.info(f"\n\ncampaign_report_markdown:\n\n")
#     logging.info(f"\n\n{campaign_report_markdown}\n\n")

#     logging.info(f"\n\search_report_markdown:\n\n")
#     logging.info(f"\n\n{search_report_markdown}\n\n")

#     logging.info(f"\n\youtube_report_markdown:\n\n")
#     logging.info(f"\n\n{youtube_report_markdown}\n\n")

#     # Convert Markdown to HTML
#     # campaign_html_content = markdown.markdown(campaign_report_markdown)
#     # html_blob = genai.types.Part.from_bytes(data = html_plot.encode('utf-8'), mime_type = 'text/html')

# except Exception as e:
#     return f"An unexpected error occurred: {e}"


# # Show artifact in the UI.
# # https://github.com/google/adk-samples/blob/main/python/agents/personalized-shopping/personalized_shopping/tools/click.py#L49C1-L58C45
# try:
#     await tool_context.save_artifact(
#         "html",
#         types.Part.from_uri(
#             file_uri=webshop_env.state["html"], mime_type="text/html"
#         ),
#     )
# except ValueError as e:
#     print(f"Error saving artifact: {e}")
