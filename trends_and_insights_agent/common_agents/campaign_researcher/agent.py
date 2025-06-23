import os
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from ...shared_libraries import callbacks, schema_types
from ...prompts import united_insights_prompt
from ...utils import MODEL
from ...tools import (
    query_web,
    # call_insights_generation_agent,
)


# Researcher 1: campaign insights
_SEQ_INSIGHT_PROMPT = """**Role:** You are a Research Assistant specializing in marketing campaign insights.

**Objective:** Your goal is to conduct web research and gather insights related to concepts from the campaign guide. These insights should answer questions like:
*  What's relevant, distinctive, or helpful about the {campaign_guide.target_product}?
*  Which key selling points would the target audience best resonate with? Why? 
*  How could marketers make a culturally relevant advertisement related to product insights?

**Available Tools:** You have access to the following tools:
*  `query_web` : Use this tool to perform web searches with Google Search.
*  `call_insights_generation_agent` : Use this tool to update the `insights` session state from the results of your web research. Do not use this tool until **after** you have completed your web research for the campaign guide.

**Instructions:** Follow these steps to complete the task at hand:
1. Use the `query_web` tool to perform Google Searches for several topics described in the `campaign_guide` (e.g., target audience, key selling points, target product, etc.)
2. Use the insights from the results in the previous step to generate a second round of Google Searches that help you better understand key features of the target product, as well as key attributes about the target audience. Use the `query_web` tool to execute these queries.
3. Given the results from the previous step, generate some insights that help establish a clear foundation for all subsequent research and ideation.
4. For each insight gathered in the previous steps, use the `call_insights_generation_agent` tool to store them in the list of structured `insights` in the session state.
5. Once this is complete, transfer to the `root_agent`.

"""

# agent tool to capture insights
insights_generator_agent = Agent(
    model=MODEL,
    name="insights_generator_agent",
    description="Gathers research insights about concepts described in the campaign guide.",
    instruction=united_insights_prompt,
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
            insight_urls: str -> Get the url(s) used to generate the insight.
            key_entities: str -> Extract any key entities discussed in the gathered context.
            key_relationships: str -> Describe the relationships between the Key Entities you have identified.
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

    logging.info(f"Final insights: {insights}")
    return {"status": "ok"}


campaign_researcher_agent = Agent(
    name="campaign_researcher_agent",
    model=MODEL,
    instruction=_SEQ_INSIGHT_PROMPT,
    description="Conducts web research specifically for product insights related to concepts defined in the `campaign_guide`",
    tools=[
        query_web,
        call_insights_generation_agent,
        # AgentTool(agent=insights_generator_agent),
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    after_agent_callback=callbacks.campaign_callback_function,
)
