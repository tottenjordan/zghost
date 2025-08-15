"""Research Orchestrator A2A Server Agent.

This agent coordinates parallel research across YouTube trends, Google Search trends,
and campaign materials, then synthesizes the results into comprehensive insights.
"""

import logging
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search, ToolContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config
from .config import config


def save_draft_report_artifact(
    report_content: str,
    filename: str,
    tool_context: ToolContext,
) -> dict:
    """
    Save draft report to session state.
    
    Args:
        report_content: The report content to save.
        filename: Name for the report file.
        tool_context: The ADK tool context.
    
    Returns:
        A status message.
    """
    # Save to session state
    tool_context.state["draft_report"] = report_content
    tool_context.state["draft_report_filename"] = filename
    
    return {
        "status": "Draft report saved successfully",
        "filename": filename,
    }


# Research orchestrator instruction
RESEARCH_ORCHESTRATOR_INSTR = """You are a research orchestrator that conducts comprehensive research for marketing campaigns.

Your main responsibilities:
1. Research Google Search trends and YouTube trends provided in the session state
2. Conduct web searches to gather insights about the trends
3. Analyze the target product and audience
4. Synthesize findings into a comprehensive research report

Workflow:
1. Review the session state for:
   - target_search_trends: Selected Google Search trends
   - target_yt_trends: Selected YouTube trends
   - target_product: The product being marketed
   - target_audience: The target audience
   - campaign_guide_data: Any campaign guide information

2. Use the `google_search` tool to research:
   - The selected trends and their cultural relevance
   - How the trends relate to the target product
   - Audience insights and preferences
   - Market opportunities

3. Synthesize your findings into a comprehensive report that includes:
   - Campaign Guide insights
   - Search Trend analysis
   - YouTube Trend analysis
   - Key insights from research
   - Recommendations for the campaign

4. Use `save_draft_report_artifact` to save the final report.

Be thorough in your research and provide actionable insights."""


# Create root_agent for a2a protocol
root_agent = Agent(
    model=config.worker_model,
    name="research_orchestrator",
    description="Orchestrate comprehensive research for the campaign metadata and trending topics.",
    instruction=RESEARCH_ORCHESTRATOR_INSTR,
    tools=[
        google_search,
        save_draft_report_artifact,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)