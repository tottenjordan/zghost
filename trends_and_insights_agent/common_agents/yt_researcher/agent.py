import os
import re
import datetime
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.planners import BuiltInPlanner
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import LongRunningFunctionTool, ToolContext, google_search
from pydantic import BaseModel, Field

from ...shared_libraries import callbacks, schema_types
from ...utils import MODEL
from ...tools import (
    # query_web,
    analyze_youtube_videos,
)

# TODO: mv to config
ADAPTIVE_THINKING_MODEL = "gemini-2.5-flash"
REASONING_MODEL = "gemini-2.5-flash"  # flash | pro


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
    url_to_short_id = callback_context.state.get("yt_url_to_short_id", {})
    sources = callback_context.state.get("yt_sources", {})
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
    callback_context.state["yt_url_to_short_id"] = url_to_short_id
    callback_context.state["yt_sources"] = sources


def citation_replacement_callback(
    callback_context: CallbackContext,
) -> types.Content:
    """Replaces citation tags in a report with Markdown-formatted links.

    Processes 'yt_final_cited_report' from context state, converting tags like
    `<cite source="src-N"/>` into hyperlinks using source information from
    `callback_context.state["yt_sources"]`. Also fixes spacing around punctuation.

    Args:
        callback_context (CallbackContext): Contains the report and source information.

    Returns:
        types.Content: The processed report with Markdown citation links.
    """
    final_report = callback_context.state.get("yt_final_cited_report", "")
    sources = callback_context.state.get("yt_sources", {})

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
    callback_context.state["final_yt_report_with_citations"] = processed_report
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

yt_web_planner = Agent(
    model=MODEL,
    name="yt_web_planner",
    description="Generates initial queries to guide web research about a trending YouTube video.",
    instruction="""
    You are a research strategist. 
    Your job is to create high-level queries that will guide web research to better understand the context of a trending YouTube video.
    
    1. Review the 'yt_video_analysis' state key to understand the video content.
    2. Generate 4-5 queries that will provide more context, such as:
        - Why the video trending.
        - The cultural significance of the trend.
        - Audiences likley to resonate with the content or context.
    
    Your output should just include a numbered list of queries. Nothing else.
    """,
    output_key="initial_yt_queries",
)


yt_web_searcher = Agent(
    model=ADAPTIVE_THINKING_MODEL,
    name="yt_web_searcher",
    description="Performs web research to better understand the context of the trending YouTube video.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a diligent and exhaustive researcher. 
    Your task is to conduct initial web research for concepts described in the 'yt_video_analysis' state key.
    You will be provided with a list of web queries in the 'initial_yt_queries' state key.
    Execute all of these queries using the 'google_search' tool and synthesize the results into a detailed summary
    """,
    tools=[google_search],
    output_key="yt_web_search_insights",
    after_agent_callback=collect_research_sources_callback,
)


yt_report_composer = Agent(
    model=REASONING_MODEL,
    name="yt_report_composer",
    include_contents="none",
    description="Transforms research data and a markdown outline into a final, cited report.",
    instruction="""
    Transform the provided data into a polished, professional, and meticulously cited research report.

    ---
    ### INPUT DATA
    *   Video Analysis: `{yt_video_analysis}`
    *   Research Guide: `{initial_yt_queries}`
    *   Final Research Findings: `{yt_web_search_insights}`
    *   Citation Sources: `{yt_sources}`

    ---
    ### CRITICAL: Citation System
    To cite a source, you MUST insert a special citation tag directly after the claim it supports.

    **The only correct format is:** `<cite source="src-ID_NUMBER" />`

    ---
    ### Final Instructions
    Generate a comprehensive report using ONLY the `<cite source="src-ID_NUMBER" />` tag system for all citations.
    Do not include a "References" or "Sources" section; all citations must be in-line.
    """,
    output_key="yt_final_cited_report",
    after_agent_callback=citation_replacement_callback,
)

yt_trends_generator_agent = Agent(
    model=MODEL,
    name="yt_trends_generator_agent",
    description="Evaluates research and analysis about the trending YouTube video to generates insights.",
    instruction="""
    Generate insights that will help marketers understand the context of the trending YouTube video.

    *Note:* an insight is a data point that: 
    *   is referenceable (with a source), 
    *   shows deep intersections between the the goal of a campaign guide and broad information sources,
    *   and is actionable i.e., provides value within the context of the campaign.

    ---
    ### Instructions
    1.  Review the 'yt_video_analysis' state key to understand what the video is about, who is involved, and what is being discussed.
    2.  Reveiw the 'yt_web_search_insights' state key to understand why this video is trending and any cultural significance.
    3.  Generate 2-3 insights from this trend research.
    
    Your response must be a single, raw JSON object validating against the 'YT_Trends' schema.
    """,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=schema_types.json_response_config,
    output_schema=schema_types.YT_Trends,
    output_key="yt_trends",
)


# research pipe
yt_research_pipeline = SequentialAgent(
    name="yt_research_pipeline",
    description="Executes a pipeline of web research related to trending YouTube videos and their contents **only**.",
    sub_agents=[
        yt_analysis_generator_agent,
        yt_web_planner,
        yt_web_searcher,
        yt_report_composer,
        yt_trends_generator_agent,
    ],
)


# yt_researcher_agent = Agent(
#     name="yt_researcher_agent",
#     model=MODEL,
#     description="Conducts web research specifically to provide additional context for trending YouTube videos.",
#     instruction="""
#     You are a web research planning assistant. 
#     Read the **workflow** below and begin with step 1 immediately. Do not deviate from these steps. 
    
#     **Important:** Do not research any topics unrelated to the YouTube video.

#     **Workflow:**
#     1. Create a high-level plan for investigating the trending YouTube video in the 'target_yt_trends' state key; include 3-4 bullets describing action-oriented research goals or themes.
#     2. Call the `yt_research_pipeline` agent to execute research and analysis.
#     """,
#     tools=[
#         # query_web,
#         # google_search,
#         # LongRunningFunctionTool(analyze_youtube_videos),
#         # call_yt_trends_generator_agent,
#         # AgentTool(agent=yt_trends_generator_agent),
#     ],
#     sub_agents=[yt_research_pipeline],
#     generate_content_config=types.GenerateContentConfig(
#         temperature=1.0,
#     ),
#     after_agent_callback=callbacks.campaign_callback_function,
# )
# # Once you have completed steps 1 and 2, transfer to the `gs_researcher_agent` agent to research trends from Google Search. Do this without collecting user input.

