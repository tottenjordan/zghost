import os
import re
import datetime
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.planners import BuiltInPlanner
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import ToolContext, google_search
from google.adk.agents.callback_context import CallbackContext
from pydantic import BaseModel, Field

from ...shared_libraries import callbacks, schema_types
from ...prompts import united_insights_prompt
from ...utils import MODEL
from ...tools import query_web


# --- Structured Output Models ---
class SearchQuery(BaseModel):
    """Model representing a specific search query for web search."""

    search_query: str = Field(
        description="A highly specific and targeted query for web search."
    )

class Feedback(BaseModel):
    """Model for providing evaluation feedback on research quality."""

    # grade: Literal["pass", "fail"] = Field(
    #     description="Evaluation result. 'pass' if the research is sufficient, 'fail' if it needs revision."
    # )
    comment: str = Field(
        description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the research."
    )
    follow_up_queries: list[SearchQuery] | None = Field(
        default=None,
        description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if the grade is 'pass'.",
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
) -> types.Content:
    """Replaces citation tags in a report with Markdown-formatted links.

    Processes 'final_cited_report' from context state, converting tags like
    `<cite source="src-N"/>` into hyperlinks using source information from
    `callback_context.state["sources"]`. Also fixes spacing around punctuation.

    Args:
        callback_context (CallbackContext): Contains the report and source information.

    Returns:
        types.Content: The processed report with Markdown citation links.
    """
    final_report = callback_context.state.get("final_cited_report", "")
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
campaign_web_planner = Agent(
    model=MODEL,
    name="campaign_web_planner",
    description="Generates initial queries to guide web research about concepts described in the campaign guide.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand concepts in the `campaign_guide`, such as the `target_audience`, `target_product`, and `key_selling_points`.
    
    The queries shoud help answer questions like:
    *  What's relevant, distinctive, or helpful about the {campaign_guide.target_product}?
    *  What are some key attributes about the target audience?
    *  Which key selling points would the target audience best resonate with? Why? 
    *  How could marketers make a culturally relevant advertisement related to product insights?
    
    Your output should just include a numbered list of queries. Nothing else.
    """,
    output_key="inital_campaign_queries",
)

campaign_web_searcher= Agent(
    model="gemini-2.5-flash",
    name="campaign_web_searcher",
    description="Performs the crucial first pass of web research about the campaign guide.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a diligent and exhaustive researcher. Your task is to conduct initial web research for concepts described in the campaign guide.
    Use the 'google_search' tool to execute all queries listed in `inital_campaign_queries`. Synthesize the results into a detailed summary.
    """,
    tools=[google_search],
    output_key="campaign_web_search_insights",
    after_agent_callback=collect_research_sources_callback,
)

campaign_web_evaluator = Agent(
    model=MODEL,
    name="campaign_web_evaluator",
    description="Critically evaluates research about the campaign guide and generates follow-up queries.",
    instruction=f"""
    You are a diligent and exhaustive researcher. 
    You are reviewing the summary results in `campaign_web_search_insights` from the first round of web research and looking for any gaps or areas that need more clarification. 

    Consider the bigger picture and the intersection of the target product and target audience. Be critical of the completeness of the research.

    If you find significant gaps in depth or coverage, write a detailed comment about what's missing, and generate 5-7 specific follow-up queries to fill those gaps.
    If the research thoroughly covers the topic, then no comment nor questions are needed.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'Feedback' schema.
    """,
    output_schema=Feedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="campaign_research_evaluation",
)

enhanced_campaign_searcher = Agent(
    model="gemini-2.5-flash",
    name="enhanced_campaign_searcher",
    description="Executes follow-up searches and integrates new findings.",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist researcher executing a refinement pass.
    You are tasked to conduct a second round of web research and gather insights related to the campaign guide, the target audience, and the target product.

    1.  Review the 'campaign_research_evaluation' state key to understand the previous round of research.
    2.  Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    3.  Synthesize the new findings and COMBINE them with the existing information in 'campaign_web_search_insights'.
    4.  Your output MUST be the new, complete, and improved set of campaign web research insights.
    """,
    tools=[google_search],
    output_key="campaign_web_search_insights",
    after_agent_callback=collect_research_sources_callback,
)

campaign_report_composer = Agent(
    model="gemini-2.5-pro",
    name="campaign_report_composer",
    include_contents="none",
    description="Transforms research data and a markdown outline into a final, cited report.",
    instruction="""
    Transform the provided data into a polished, professional, and meticulously cited research report.

    ---
    ### INPUT DATA
    *   Research Plan: `{inital_campaign_queries}`
    *   Research Critiques: `{campaign_research_evaluation}`
    *   Final Research Findings: `{campaign_web_search_insights}`
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
    output_key="final_cited_report",
    after_agent_callback=citation_replacement_callback,
)

campaign_research_pipeline = SequentialAgent(
    name="campaign_research_pipeline",
    description="Executes a pipeline of web research related to the campaign guide. It performs iterative research, evaluation, and insight generation.",
    sub_agents=[
        campaign_web_planner,
        campaign_web_searcher,
        campaign_web_evaluator,
        enhanced_campaign_searcher,
        campaign_report_composer,
    ],
)

insights_generator_agent = Agent(
    model=MODEL,
    name="insights_generator_agent",
    description="Critically evaluates all research about the campaign guide and generates insights.",
    instruction=f"""
    You are a diligent and exhaustive researcher. 
    You are tasked with gathering insights from the campaign web research. 
    
    *Note:* an insight is a data point that: 
    *   is referenceable (with a source), 
    *   shows deep intersections between the the goal of a campaign guide and broad information sources,
    *   and is actionable i.e., provides value within the context of the campaign.
    
    ---
    ### Instructions
    1.  Review the 'final_cited_report' state key to understand the completed campaign research
    2.  Generate 5-7 insights that follow this schema:
    
    Your response must be a single, raw JSON object validating against the 'Insights' schema.
    """,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=schema_types.json_response_config,
    output_schema=schema_types.Insights,
    output_key="insights",
)

async def call_insights_generation_agent(
    question: str, tool_context: ToolContext
) -> dict:
    """
    Tool to call the `insights_generator_agent` agent. Use this tool to update `insights` in the session state.

    Args:
        Question: The question to ask the agent, use the tool_context to extract the following schema:
            insight_title: str -> Come up with a unique title for the insight.
            insight_text: str -> Generate a summary of the insight from the web research.
            insight_urls: list[str] -> Get the url(s) used to generate the insight.
            key_entities: list[str] -> Extract any key entities discussed in the gathered context.
            key_relationships: list[str] -> Describe the relationships between the Key Entities you have identified.
            key_audiences: str -> Considering the guide, how does this insight intersect with the audience?
            key_product_insights: str -> Considering the guide, how does this insight intersect with the product?
        tool_context: The tool context.
    """
    agent_tool = AgentTool(insights_generator_agent)
    existing_insights = tool_context.state.get("insights")
    insights = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    if existing_insights is not {"insights": []}:
        insights["insights"].extend(existing_insights["insights"])
    tool_context.state["insights"] = insights
    # logging.info(f"\n\n Final `insights`: {insights} \n\n")
    return {"status": "ok"}


campaign_researcher_agent = Agent(
    name="campaign_researcher_agent",
    model=MODEL,
    description="Conducts web research specifically for product insights related to concepts defined in the campaign guide",
    instruction="""
    You are a web research planning assistant. Your primary task is to execute a research pipeline that conducts web research related to the campaign guide.
    Do not perform any research yourself. Just execute the research pipeline and update the insights.

    Your workflow is:
    1.  Execute the `campaign_research_pipeline` sub-agent.
    2.  Once the research pipeline is complete, read the summary in `final_cited_report` and generate relevant insights. 
    3.  For each insight, use the `call_insights_generation_agent` tool to store them in the `insights` state variable.

    Once these steps are complete, confirm with the user. Once the user confirms, transfer back to the `root_agent`.
    """,
    tools=[
        # query_web,
        call_insights_generation_agent,
    ],
    sub_agents=[campaign_research_pipeline],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    # after_agent_callback=callbacks.campaign_callback_function,
)

# Once these two steps are complete, confirm with the user. Once the user confirms, transfer back to the `root_agent`.