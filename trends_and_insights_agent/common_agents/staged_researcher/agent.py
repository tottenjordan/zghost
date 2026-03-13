import datetime
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import google_search
from google.adk.planners import BuiltInPlanner
from google.adk.agents import Agent, SequentialAgent, ParallelAgent

from trends_and_insights_agent.shared_libraries.config import config
from trends_and_insights_agent.shared_libraries import callbacks, schema_types

from .tools import save_draft_report_artifact, recall_prior_insights
from .sub_agents.campaign_web_researcher.agent import ca_sequential_planner
from .sub_agents.search_web_researcher.agent import gs_sequential_planner
from .sub_agents.youtube_web_researcher.agent import yt_sequential_planner


# --- PARALLEL RESEARCH SUBAGENTS --- #
parallel_planner_agent = ParallelAgent(
    name="parallel_planner_agent",
    sub_agents=[yt_sequential_planner, gs_sequential_planner, ca_sequential_planner],
    description="Runs multiple research planning agents in parallel.",
)

merge_planners = Agent(
    name="merge_planners",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    instruction="""You are an AI Assistant responsible for combining initial research findings into a comprehensive summary.
    Your primary task is to organize the following research summaries, clearly attributing findings to their source areas. 
    Structure your response using headings for each topic. Ensure the report is coherent and integrates the key points smoothly.

    ---
    **Output Format:**

    # Summary of Campaign and Trend Research

    ## Campaign Guide
    {campaign_web_search_insights}

    ## Search Trend
    {gs_web_search_insights}

    ## YouTube Trends Findings
    {yt_web_search_insights}

    Output *only* the structured report following this format. Do not include introductory or concluding phrases outside this structure, and strictly adhere to using only the provided input summary content.
    """,
    output_key="combined_web_search_insights",
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)

merge_parallel_insights = SequentialAgent(
    name="merge_parallel_insights",
    sub_agents=[parallel_planner_agent, merge_planners],
    description="Coordinates parallel research and synthesizes the results.",
)


# --- COMBINED RESEARCH SUBAGENTS --- #
combined_web_evaluator = Agent(
    model=config.critic_model,
    name="combined_web_evaluator",
    description="Critically evaluates research about the campaign guide and generates follow-up queries.",
    instruction=f"""
    You are a meticulous quality assurance analyst evaluating the research findings in 'combined_web_search_insights'.
    
    Be critical of the completeness of the research.
    Consider the bigger picture and the intersection of the `target_product` and `target_audience`. 
    Consider the trends in each of the 'target_search_trends' and 'target_yt_trends' state keys.
    
    Look for any gaps in depth or coverage, as well as any areas that need more clarification. 
        - If you find significant gaps in depth or coverage, write a detailed comment about what's missing, and generate 5-7 specific follow-up queries to fill those gaps.
        - If you don't find any significant gaps, write a detailed comment about any aspect of the campaign guide or trends to research further. Provide 5-7 related queries.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'CampaignFeedback' schema.
    """,
    output_schema=schema_types.CampaignFeedback,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="combined_research_evaluation",
    before_model_callback=[callbacks.before_model_status_callback, callbacks.rate_limit_callback],
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)


enhanced_combined_searcher = Agent(
    model=config.worker_model,
    name="enhanced_combined_searcher",
    description="Executes follow-up searches and integrates new findings.",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    instruction="""
    You are a specialist researcher executing a refinement pass.
    You are tasked to conduct a second round of web research and gather insights related to the trending YouTube video, the trending Search terms, the target audience, and the target product.

    1.  First, call `recall_prior_insights` with the brand and product from session state to retrieve learnings from previous campaigns. This gives you historical context.
    2.  Review the 'combined_research_evaluation' state key to understand the previous round of research.
    3.  Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    4.  Synthesize the new findings and COMBINE them with the existing information in 'combined_web_search_insights'.
    5.  If prior campaign insights were retrieved, incorporate relevant learnings into your synthesis (e.g., what messaging worked before, audience preferences, successful creative approaches).
    6.  Your output MUST be the new, complete, and improved set of research insights for the trending Search terms, trending YouTube video, and campaign guide.
    """,
    tools=[google_search, recall_prior_insights],
    output_key="combined_web_search_insights",
    after_agent_callback=callbacks.collect_research_sources_callback,
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)


combined_report_composer = Agent(
    model=config.critic_model,
    name="combined_report_composer",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    include_contents="none",
    description="Transforms research data and a markdown outline into a final, cited report.",
    instruction="""
    Transform the provided data into a polished, professional, and meticulously cited research report.

    ---
    **INPUT DATA**

    *   **Search Trends:**
        {target_search_trends}

    *   **YouTube Trends:**
        {target_yt_trends}

    *   **YouTube Video Analysis:**
        {yt_video_analysis}
    
    *   **Final Research:**
        {combined_web_search_insights}
    
    *   **Citation Sources:**
        `{sources}`

    *   **Prior Campaign Insights (from Memory Bank):**
        {prior_campaign_insights}

    ---
    **CRITICAL: Citation System**
    To cite a source, you MUST insert a special citation tag directly after the claim it supports.

    **The only correct format is:** `<cite source="src-ID_NUMBER" />`

    ---
    **OUTPUT FORMAT**
    Organize the output to include these sections:
    *   **Campaign Guide**
    *   **Search Trend**
    *   **YouTube Trend**
    *   **Key Insights from Research**

    You can use any format you prefer, but here's a suggested structure:
    # Campaign Title
    ## Section Name
    An overview of what this section covers, including specific insights from web research.
    Feel free to add subsections or bullet points if needed to better organize the content.
    Make sure your outline is clear and easy to follow.

    ---
    **Final Instructions**
    Generate a comprehensive report using ONLY the `<cite source="src-ID_NUMBER" />` tag system for all citations.
    Ensure the final report follows a structure similar to the one proposed in the **OUTPUT FORMAT**
    Do not include a "References" or "Sources" section; all citations must be in-line.
    """,
    output_key="combined_final_cited_report",
    after_agent_callback=callbacks.citation_replacement_callback,
    before_model_callback=[callbacks.before_model_status_callback, callbacks.rate_limit_callback],
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)


# --- COMPLETE RESEARCH PIPELINE SUBAGENT --- #
combined_research_pipeline = SequentialAgent(
    name="combined_research_pipeline",
    description="Executes a pipeline of web research. It performs iterative research, evaluation, and insight generation.",
    sub_agents=[
        merge_parallel_insights,
        combined_web_evaluator,
        enhanced_combined_searcher,
        combined_report_composer,
    ],
)


# Agent that saves the research report as a PDF artifact after the pipeline completes
report_saver_agent = Agent(
    model=config.worker_model,
    name="report_saver_agent",
    description="Saves research report as PDF artifact.",
    instruction="Use save_draft_report_artifact to save the combined_final_cited_report as PDF. Then stop.",
    tools=[save_draft_report_artifact],
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)

# Main orchestrator — SequentialAgent so all intermediate events (including
# ui:status_update state deltas) flow to GE in real-time instead of being
# buffered inside an AgentTool's isolated runner.
research_orchestrator = SequentialAgent(
    name="research_orchestrator",
    description="Orchestrate comprehensive research for the campaign metadata and trending topics.",
    sub_agents=[combined_research_pipeline, report_saver_agent],
    after_agent_callback=callbacks.save_research_to_memory,
)
