import os
import re
import datetime
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.planners import BuiltInPlanner
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.tools import LongRunningFunctionTool, google_search

from ...shared_libraries import callbacks, schema_types
from ...shared_libraries.config import config
from ...tools import analyze_youtube_videos


# --- AGENT DEFINITIONS --- #

# --- PARALLEL RESEARCH SUBAGENTS --- #

# --- YouTube Trend Research Planner --- #
yt_analysis_generator_agent = Agent(
    model=config.worker_model,
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
    model=config.lite_planner_model,
    name="gs_web_planner",
    description="Generates initial queries to understand why the 'target_yt_trends' are trending.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand the cultural significance of trending YouTube videos.
    
    1. Read the 'yt_video_analysis' state key to understand the trending YouTube video.
    2. Generate 2-3 web queries to better understanding the context of the video.
    
    Your output should just include a numbered list of queries. Nothing else.
    """,
    output_key="initial_yt_queries",
)
yt_web_searcher = Agent(
    model=config.worker_model,
    name="yt_web_searcher",
    description="Performs web research to better understand the context of the trending YouTube video.",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False)
    ),
    instruction="""
    You are a diligent and exhaustive researcher. 
    Your task is to conduct initial web research for concepts described in the 'yt_video_analysis' state key.
    You will be provided with a list of web queries in the 'initial_yt_queries' state key.
    Execute all of these queries using the 'google_search' tool and synthesize the results into a detailed summary
    """,
    tools=[google_search],
    output_key="yt_web_search_insights",
    after_agent_callback=callbacks.collect_research_sources_callback,
)
yt_sequential_planner = SequentialAgent(
    name="yt_sequential_planner",
    description="Executes sequential research tasks for trending YouTube videos.",
    sub_agents=[yt_analysis_generator_agent, yt_web_planner, yt_web_searcher],
)

# --- Google Search Trend Research Planner --- #
gs_web_planner = Agent(
    model=config.lite_planner_model,
    name="gs_web_planner",
    description="Generates initial queries to understand why the 'target_search_trends' are trending.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand the cultural significance of trends from Google Search.

    Review the search trend(s) provided in the **Input Data**, then proceed to the **Instructions**.

    ---
    **Input Data**

    <SEARCH_TRENDS>
    {target_search_trends}
    </SEARCH_TRENDS>
    
    ---
    **Instructions**
    1. Read the 'target_search_trends' state key to get the Search trend.
    2. Generate 4-5 queries that will provide more context for this trend, and answer questions like:
        - Why are these search terms trending? Who is involved?
        - Are there any related themes that would resonate with our target audience?
        - Describe any key entities involved (i.e., people, places, organizations, named events, etc.), and the relationships between these key entities, especially in the context of the trending topic, or if possible the target product
        - Explain the cultural significance of the trend.
    
    **CRITICAL RULE: Your output should just include a numbered list of queries. Nothing else.**
    """,
    output_key="initial_gs_queries",
)
gs_web_searcher = Agent(
    model=config.worker_model,
    name="gs_web_searcher",
    description="Performs the crucial first pass of web research about the trending Search terms.",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False)
    ),
    instruction="""
    You are a diligent and exhaustive researcher. 
    Your task is to conduct initial web research for the trending Search terms.
    Use the 'google_search' tool to execute all queries listed in 'initial_gs_queries'. 
    Synthesize the results into a detailed summary.
    """,
    tools=[google_search],
    output_key="gs_web_search_insights",
    after_agent_callback=callbacks.collect_research_sources_callback,
)
gs_sequential_planner = SequentialAgent(
    name="gs_sequential_planner",
    description="Executes sequential research tasks for trends in Google Search.",
    sub_agents=[gs_web_planner, gs_web_searcher],
)

# --- Campaign Guide Research Planner --- #
campaign_web_planner = Agent(
    model=config.lite_planner_model,
    name="campaign_web_planner",
    description="Generates initial queries to guide web research about concepts described in the `campaign_guide`.",
    instruction="""You are a research strategist. 
    Your job is to create high-level queries that will help marketers better understand concepts described in the 'campaign_guide' state key.
     
    Review the concepts from the campaign guide provided in the **Input Data**, then generate a list of 4-6 web queries to better understand them.

    ---
    **Input Data**

    <TARGET_AUDIENCE>
    {target_audience}
    </TARGET_AUDIENCE>

    <TARGET_PRODUCT>
    {target_product}
    </TARGET_PRODUCT>
    
    <KEY_SELLING_POINTS>
    {key_selling_points}
    </KEY_SELLING_POINTS>
    
    ---
    **Important Guidelines**
    The queries should help answer questions like:
    *  What's relevant, distinctive, or helpful about the {target_product}?
    *  What are some key attributes about the target audience?
    *  Which key selling points would the target audience best resonate with? Why? 
    *  How could marketers make a culturally relevant advertisement related to product insights?
    
    ---
    **Final Instructions**
    Generate a list of web queries that addresses the **Important Guidelines**.
    **CRITICAL RULE: Your output should just include a numbered list of queries. Nothing else.**
    """,
    output_key="initial_campaign_queries",
)
campaign_web_searcher = Agent(
    model=config.worker_model,
    name="campaign_web_searcher",
    description="Performs the crucial first pass of web research about the campaign guide.",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""
    You are a diligent and exhaustive researcher. Your task is to conduct initial web research for concepts described in the campaign guide.
    You will be provided with a list of web queries in the 'initial_campaign_queries' state key.
    Use the 'google_search' tool to execute all queries. 
    Synthesize the results into a detailed summary.
    """,
    tools=[google_search],
    output_key="campaign_web_search_insights",
    after_agent_callback=callbacks.collect_research_sources_callback,
)
ca_sequential_planner = SequentialAgent(
    name="ca_sequential_planner",
    description="Executes sequential research tasks for concepts described in the campaign guide.",
    sub_agents=[campaign_web_planner, campaign_web_searcher],
)


parallel_planner_agent = ParallelAgent(
    name="parallel_planner_agent",
    sub_agents=[yt_sequential_planner, gs_sequential_planner, ca_sequential_planner],
    description="Runs multiple research planning agents in parallel.",
)


merge_planners = Agent(
    name="merge_planners",
    model=config.worker_model,
    # include_contents="none",
    description="Combine results from state keys 'campaign_web_search_insights', 'gs_web_search_insights', and 'yt_web_search_insights'",
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
)


merge_parallel_insights = SequentialAgent(
    name="merge_parallel_insights",
    sub_agents=[parallel_planner_agent, merge_planners],
    description="Coordinates parallel research and synthesizes the results.",
)


# --- COMBINED RESEARCH SUBAGENTS ---
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
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="combined_research_evaluation",
    before_model_callback=callbacks.rate_limit_callback,
)


enhanced_combined_searcher = Agent(
    model=config.worker_model,
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
    after_agent_callback=callbacks.collect_research_sources_callback,
)


combined_report_composer = Agent(
    model=config.critic_model,
    name="combined_report_composer",
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
    An overview of what this section covers
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
    before_model_callback=callbacks.rate_limit_callback,
)


# --- PIPELINE RESEARCH SUBAGENT ---
combined_research_pipeline = SequentialAgent(
    name="combined_research_pipeline",
    description="Executes a pipeline of web research related to the trending Search terms, trending YouTube videos, and the campaign guide. It performs iterative research, evaluation, and insight generation.",
    sub_agents=[
        merge_parallel_insights,
        combined_web_evaluator,
        enhanced_combined_searcher,
        combined_report_composer,
    ],
)
