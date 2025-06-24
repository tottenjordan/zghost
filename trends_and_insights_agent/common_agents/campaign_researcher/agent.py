import os
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.planners import BuiltInPlanner
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import ToolContext, google_search
from google.adk.agents.callback_context import CallbackContext

from ...shared_libraries import callbacks, schema_types
from ...prompts import united_insights_prompt
from ...utils import MODEL
from ...tools import query_web


# Callbacks
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


# Agent Tools
initial_campaign_planner = Agent(
    model=MODEL,
    name="initial_campaign_planner",
    description="Generates initial web research queries about concepts described in the campaign guide.",
    instruction="""
    You are a research strategist. Your job is to create several queries that help guide the web research. 
    
    The queries shoud help answer questions like:
    *  What's relevant, distinctive, or helpful about the {campaign_guide.target_product}?
    *  What are some key attributes about the target audience?
    *  Which key selling points would the target audience best resonate with? Why? 
    *  How could marketers make a culturally relevant advertisement related to product insights?
    
    Your output should just include a numbered list of questions. Nothing else.
    """,
    output_key="inital_campaign_queries",
)

initial_campaign_search = Agent(
    model="gemini-2.5-flash",
    name="initial_campaign_search",
    description="Performs the crucial first pass of web research about the campaign guide.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a diligent and exhaustive researcher. Your task is to perform the initial web research for concepts described in the campaign guide.

    Execute all queries listed in `inital_campaign_queries` using the 'google_search' tool and synthesize the results into a detailed summary.
    """,
    tools=[google_search],
    output_key="initial_campaign_search_findings",
    after_agent_callback=collect_research_sources_callback,
)

initial_campaign_evaluator = Agent(
    model=MODEL,
    name="initial_campaign_evaluator",
    description="Critically evaluates research about the campaign guide and generates follow-up queries.",
    instruction=f"""
    You are a diligent and exhaustive researcher. 
    You are preparing for a second round of web research that helps you better understand the insights gathered during the initial campaign web research. 
    
    Read the summary in `initial_campaign_search_findings` and generate a list of queries. 
    These queries should help you understand:
    *  They messaging to best reach the target audience 
    *  Features about the target product that will best resonate with the target audience

    Your output should just include a numbered list of questions. Nothing else.
    """,
    output_key="follow_up_queries",
)

enhanced_campaign_search = Agent(
    model="gemini-2.5-flash",
    name="enhanced_campaign_search",
    description="Executes follow-up searches and integrates new findings.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a specialist researcher executing a refinement pass.
    You are tasked to conduct a second round of web research and gather insights related to the campaign guide, the target audience, and the target product.

    1.  Review the 'initial_campaign_search_findings' state key to understand the initial round of research.
    2.  Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    3.  Synthesize the new findings and COMBINE them with the existing information in 'initial_campaign_search_findings'.
    4.  Your output MUST be the new, complete, and improved set of research findings.
    """,
    tools=[google_search],
    output_key="campaign_web_search_insights",
    after_agent_callback=collect_research_sources_callback,
)


campaign_research_pipeline = SequentialAgent(
    name="campaign_research_pipeline",
    description="Executes multiple rounds of web research rlated to the campaign guide. It performs iterative research, evaluation, and insight generation.",
    sub_agents=[
        initial_campaign_planner,
        initial_campaign_search,
        initial_campaign_evaluator,
        enhanced_campaign_search,
        # insights_generator_agent,
    ],
)


insights_generator_agent = Agent(
    model=MODEL,
    name="insights_generator_agent",
    description="Critically evaluates all research about the campaign guide and generates insights.",
    instruction=f"""
    You are a diligent and exhaustive researcher. 
    You are tasked with generating insights that will help expert marketers better understand the the target audience and the target product.
    
    1.  Review the 'campaign_web_search_insights' state key to understand the completed campaign research.
    2.  Generate a set of insights to summarize this research.

    Once these two steps are complete, confirm with the user. Once the user confirms, transfer back to the `root_agent`.
    """,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=schema_types.json_response_config,
    output_schema=schema_types.Insights,
    output_key="insights",
)

# insights_generator_agent = Agent(
#     model=MODEL,
#     name="insights_generator_agent",
#     description="Gathers research insights about concepts described in the campaign guide.",
#     instruction=united_insights_prompt,
#     disallow_transfer_to_parent=True,
#     disallow_transfer_to_peers=True,
#     generate_content_config=schema_types.json_response_config,
#     output_schema=schema_types.Insights,
#     output_key="insights",
# )


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
    logging.info(f"\n\n Final `insights`: {insights} \n\n")
    return {"status": "ok"}


# # Researcher 1: campaign insights
# _SEQ_INSIGHT_PROMPT = """**Role:** You are a Research Assistant specializing in marketing campaign insights.

# **Objective:** Your goal is to conduct web research and gather insights related to concepts from the campaign guide. These insights should answer questions like:
# *  What's relevant, distinctive, or helpful about the {campaign_guide.target_product}?
# *  Which key selling points would the target audience best resonate with? Why?
# *  How could marketers make a culturally relevant advertisement related to product insights?

# **Available Tools:** You have access to the following tools:
# *  `google_search` : Use this tool to perform web searches with Google Search.
# *  `call_insights_generation_agent` : Use this tool to update the `insights` session state from the results of your web research. Do not use this tool until **after** you have completed your web research for the campaign guide.

# **Instructions:** Follow these steps to complete the task at hand:
# 1. Use the `google_search` tool to perform Google Searches for several topics described in the `campaign_guide` (e.g., target audience, key selling points, target product, etc.)
# 2. Use insights from the results in the previous step to generate a second round of Google Searches that help you better understand key features of the target product, as well as key attributes about the target audience. Use the `google_search` tool to execute these queries.
# 3. Given the results from the previous step, generate some insights that help establish a clear foundation for all subsequent research and ideation.
# 4. For each insight gathered in the previous steps, use the `call_insights_generation_agent` tool to store them in the list of structured `insights` in the session state.
# 5. Confirm with the user before proceeding. Once the user is satisfied, transfer to the `root_agent`.

# """

campaign_researcher_agent = Agent(
    name="campaign_researcher_agent",
    model=MODEL,
    description="Conducts web research specifically for product insights related to concepts defined in the `campaign_guide`",
    # instruction=_SEQ_INSIGHT_PROMPT,
    instruction="""
    You are a web research planning assistant. Your primary task is to execute a research pipeline that conducts web research related to the campaign guide.
    Do not perform any research yourself. Just execute the research pipeline and update the insights.

    Your workflow is:
    1.  Execute the `campaign_research_pipeline` sub-agent research pipeline.
    2.  Read the summary in `campaign_web_search_insights`. Generate insights from this research. 
    3.  For each insight, use the `call_insights_generation_agent` tool to store them in the list of structured `insights` in the session state.

    Once these steps are complete, confirm with the user. Once the user has confirmed, transfer back to the `root_agent`.
    """,
    tools=[
        # query_web,
        call_insights_generation_agent,
    ],
    sub_agents=[campaign_research_pipeline],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    after_agent_callback=callbacks.campaign_callback_function,
)
