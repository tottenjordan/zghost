import os
import re
import datetime
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.planners import BuiltInPlanner
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import LongRunningFunctionTool, ToolContext, google_search
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field

from ...shared_libraries import callbacks, schema_types
from ...tools import analyze_youtube_videos
from ...utils import MODEL

# TODO: mv to config
ADAPTIVE_THINKING_MODEL = "gemini-2.5-flash"
REASONING_MODEL = "gemini-2.5-pro"


# --- Structured Output Models ---
class CampaignSearchQuery(BaseModel):
    """Model representing a specific search query for web search."""

    search_query: str = Field(
        description="A highly specific and targeted query for web search."
    )


class CampaignFeedback(BaseModel):
    """Model for providing evaluation feedback on research quality."""

    comment: str = Field(
        description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the research."
    )
    follow_up_queries: list[CampaignSearchQuery] | None = Field(
        default=None,
        description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if no follow-up questions needed.",
    )


# --- Callbacks ---
def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources and their supported claims from agent events.

    This function processes the agent's `session.events` to extract web source details (URLs,
    titles, domains from `grounding_chunks`) and associated text segments with confidence scores
    (from `grounding_supports`). The aggregated source information and a mapping of URLs to short
    IDs are cumulatively stored in `callback_context.state`.

    Args:
        callback_context (CallbackContext): The context object providing access to the agent's
            session events and persistent state.
    """
    session = callback_context._invocation_context.session
    url_to_short_id = callback_context.state.get("url_to_short_id", {})
    sources = callback_context.state.get("sources", {})
    id_counter = len(url_to_short_id) + 1
    for event in session.events:
        if not (event.grounding_metadata and event.grounding_metadata.grounding_chunks):
            continue
        chunks_info = {}
        for idx, chunk in enumerate(event.grounding_metadata.grounding_chunks):
            if not chunk.web:
                continue
            url = chunk.web.uri
            title = (
                chunk.web.title
                if chunk.web.title != chunk.web.domain
                else chunk.web.domain
            )
            if url not in url_to_short_id:
                short_id = f"src-{id_counter}"
                url_to_short_id[url] = short_id
                sources[short_id] = {
                    "short_id": short_id,
                    "title": title,
                    "url": url,
                    "domain": chunk.web.domain,
                    "supported_claims": [],
                }
                id_counter += 1
            chunks_info[idx] = url_to_short_id[url]
        if event.grounding_metadata.grounding_supports:
            for support in event.grounding_metadata.grounding_supports:
                confidence_scores = support.confidence_scores or []
                chunk_indices = support.grounding_chunk_indices or []
                for i, chunk_idx in enumerate(chunk_indices):
                    if chunk_idx in chunks_info:
                        short_id = chunks_info[chunk_idx]
                        confidence = (
                            confidence_scores[i] if i < len(confidence_scores) else 0.5
                        )
                        text_segment = support.segment.text if support.segment else ""
                        sources[short_id]["supported_claims"].append(
                            {
                                "text_segment": text_segment,
                                "confidence": confidence,
                            }
                        )
    callback_context.state["url_to_short_id"] = url_to_short_id
    callback_context.state["sources"] = sources


def citation_replacement_callback(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Replaces citation tags in a report with Markdown-formatted links.

    Processes 'combined_final_cited_report' from context state, converting tags like
    `<cite source="src-N"/>` into hyperlinks using source information from
    `callback_context.state["sources"]`. Also fixes spacing around punctuation.

    Args:
        callback_context (CallbackContext): Contains the report and source information.

    Returns:
        types.Content: The processed report with Markdown citation links.
    """
    # types.Content: The processed report with Markdown citation links.
    final_report = callback_context.state.get("combined_final_cited_report", "")
    sources = callback_context.state.get("sources", {})

    def tag_replacer(match: re.Match) -> str:
        short_id = match.group(1)
        if not (source_info := sources.get(short_id)):
            logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
            return ""
        display_text = source_info.get("title", source_info.get("domain", short_id))
        return f" [{display_text}]({source_info['url']})"

    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>',
        tag_replacer,
        final_report,
    )
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)
    callback_context.state["final_report_with_citations"] = processed_report
    return types.Content(parts=[types.Part(text=processed_report)])


# --- AGENT DEFINITIONS ---
yt_analysis_generator_agent = Agent(
    model=MODEL,
    name="yt_analysis_generator_agent",
    description="Process YouTube videos, extract key details, and provide an overall summary.",
    instruction="""
    Your goal is to **understand the content** of the trending YouTube video in the 'target_yt_trends' state key.
    
    1. Review the 'target_yt_trends' state key and use the `analyze_youtube_videos` tool to analyze the 'video_url'.
    2. Provide a concise summary covering:
        - **Main Thesis/Claim:** What is the video about? What is being discussed?
        - **Key Entities:** Describe any key entities (e.g., people, places, things) involved and how they are related. 
        - **Trend Context:** Why might this video be trending?
        - **Summary:** Provide a concise summary of the video content.
    """,
    tools=[
        LongRunningFunctionTool(analyze_youtube_videos),
    ],
    output_key="yt_video_analysis",
)


gs_web_planner = Agent(
    model=MODEL,
    name="gs_web_planner",
    description="Generates initial queries to understand why the 'target_search_trends' are trending.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand the cultural significance of a trend in Google Search.
    
    1. Read the 'target_search_trends' state key to get the Search trend.
    2. Generate 4-5 queries that will provide more context, and answer questions like:
        - Why are these search terms trending? Who is involved?
        - Are there any related themes that would resonate with our target audience?
        - Describe any key entities involved (i.e., people, places, organizations, named events, etc.), and the relationships between these key entities, especially in the context of the trending topic, or if possible the target product
        - Explain the cultural significance of the trend. 
    
    Your output should just include a numbered list of queries. Nothing else.
    """,
    output_key="inital_gs_queries",
)


campaign_web_planner = Agent(
    model=MODEL,
    name="campaign_web_planner",
    description="Generates initial queries to guide web research about concepts described in the campaign guide.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand concepts in the 'campaign_guide', such as the 'target_audience', 'target_product', and 'key_selling_points'.
    
    The queries shoud help answer questions like:
    *  What's relevant, distinctive, or helpful about the 'target_product'?
    *  What are some key attributes about the target audience?
    *  Which key selling points would the target audience best resonate with? Why? 
    *  How could marketers make a culturally relevant advertisement related to product insights?
    
    Your output should just include a numbered list of queries. Nothing else.
    """,
    output_key="inital_campaign_queries",
)


combined_web_searcher = Agent(
    model=ADAPTIVE_THINKING_MODEL,
    name="combined_web_searcher",
    description="Performs the crucial first pass of web research about the campaign guide, search trend, and trending youtube video.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a highly capable and diligent research and synthesis agent. Your comprehensive task is to execute a provided research plan with **absolute fidelity**, first by gathering necessary information, and then by synthesizing that information into specified outputs.

    You will be provided with two sets of web queries, stored in the 'inital_gs_queries' and 'inital_campaign_queries' state keys.

    1. For each list of queries (e.g., the 'inital_gs_queries', and 'inital_campaign_queries' state keys):
        *   **Execution:** Utilize the `google_search` tool to execute **all** web queries in the list
        *   **Summarization:** Synthesize the search results into a detailed, coherent summary.

    2. Generate a report documenting each summary from Step 1.
    """,
    tools=[google_search],
    output_key="combined_web_search_insights",
    after_agent_callback=collect_research_sources_callback,
)


combined_web_evaluator = Agent(
    model=REASONING_MODEL,
    name="combined_web_evaluator",
    description="Critically evaluates research about the campaign guide and generates follow-up queries.",
    instruction=f"""
    You are a meticulous quality assurance analyst evaluating the research findings in 'combined_web_search_insights'.
    
    Be critical of the completeness of the research.
    Consider the bigger picture and the intersection of the target product and target audience. 
    Consider the trends from Google Search and YouTube.
    
    Look for any gaps in depth or coverage, as well as any areas that need more clarification. 
        - If you find significant gaps in depth or coverage, write a detailed comment about what's missing, and generate 5-7 specific follow-up queries to fill those gaps.
        - If you don't find any significant gaps, write a detailed comment about any aspect of the campaign guide or trends to research further. Provide 5-7 related queries.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'CampaignFeedback' schema.
    """,
    output_schema=CampaignFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="combined_research_evaluation",
)


enhanced_combined_searcher = Agent(
    model=ADAPTIVE_THINKING_MODEL,
    name="enhanced_combined_searcher",
    description="Executes follow-up searches and integrates new findings.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a specialist researcher executing a refinement pass.
    You are tasked to conduct a second round of web research and gather insights related to the trending YouTube video, the trending Search terms, the target audience, and the target product.

    1.  Review the 'combined_research_evaluation' state key to understand the previous round of research.
    2.  Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    3.  Synthesize the new findings and COMBINE them with the existing information in 'combined_web_search_insights'.
    4.  Your output MUST be the new, complete, and improved set of research insights for the trending Search terms, trending YouTube video, and campaign guide.
    """,
    tools=[google_search],
    output_key="combined_web_search_insights",
    after_agent_callback=collect_research_sources_callback,
)


combined_report_composer = Agent(
    model=REASONING_MODEL,
    name="combined_report_composer",
    include_contents="none",
    description="Transforms research data and a markdown outline into a final, cited report.",
    instruction="""
    Transform the provided data into a polished, professional, and meticulously cited research report.

    ---
    ### INPUT DATA
    *   Video Analysis: `{yt_video_analysis}`
    *   Search Trend Guide: `{inital_gs_queries}`
    *   Campaign Research Guide: `{inital_campaign_queries}`
    *   Research Critiques: `{combined_research_evaluation}`
    *   Final Research Findings: `{combined_web_search_insights}`
    *   Citation Sources: `{sources}`

    ---
    ### CRITICAL: Citation System
    To cite a source, you MUST insert a special citation tag directly after the claim it supports.

    **The only correct format is:** `<cite source="src-ID_NUMBER" />`

    ---
    ### Final Instructions
    Generate a comprehensive report using ONLY the `<cite source="src-ID_NUMBER" />` tag system for all citations.
    Do not include a "References" or "Sources" section; all citations must be in-line.
    """,
    output_key="combined_final_cited_report",
    after_agent_callback=citation_replacement_callback,
)


combined_research_pipeline = SequentialAgent(
    name="combined_research_pipeline",
    description="Executes a pipeline of web research related to the trending Search terms, trending YouTube videos, and the campaign guide. It performs iterative research, evaluation, and insight generation.",
    sub_agents=[
        yt_analysis_generator_agent,
        gs_web_planner,
        campaign_web_planner,
        combined_web_searcher,
        combined_web_evaluator,
        enhanced_combined_searcher,
        combined_report_composer,
    ],
)
