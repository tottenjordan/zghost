import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import google_search
from google.adk.planners import BuiltInPlanner
from google.adk.agents import Agent, SequentialAgent

from trends_and_insights_agent.shared_libraries import callbacks
from trends_and_insights_agent.shared_libraries.config import config


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
