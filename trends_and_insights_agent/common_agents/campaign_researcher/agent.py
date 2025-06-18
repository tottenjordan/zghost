import os
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent

# from google.adk.agents.llm_agent import LlmAgent
# from google.adk.tools.agent_tool import AgentTool

# from ...shared_libraries.types import json_response_config
from ...utils import MODEL, campaign_callback_function
from ...tools import (
    query_web,
    call_insights_generation_agent,
)


# Researcher 1: campaign insights
_SEQ_INSIGHT_PROMPT = """**Role:** You are a Research Assistant specializing in marketing campaign insights.

**Objective:** Your goal is to conduct web research and gather insights related to concepts from the campaign guide. These insights should answer questions like:
*  What's relevant, distinctive, or helpful about the {campaign_guide.target_product} or {campaign_guide.brand}?
*  Which product features would the target audience best resonate with?
*  How could marketers make a culturally relevant advertisement related to product insights?

**Available Tools:** You have access to the following tools:
*  `query_web` : Use this tool to perform web searches with Google Search.
*  `call_insights_generation_agent` : Use this tool to update the `insights` session state from the results of your web research.

**Instructions:** Follow these steps to complete the task at hand:
1. Use the `query_web` tool to perform Google Searches for several topics described in the `campaign_guide` (e.g., attributes about the target_audience, key features about the target_product, etc.)
2. Given the results from the previous step, generate some insights that help establish a clear foundation for all subsequent research and ideation.
3. For each insight, use the `call_insights_generation_agent` tool to update the list of structured `insights` in the session state.

Once these steps are complete, transfer back to the root agent.

"""

campaign_researcher_agent = Agent(
    name="campaign_researcher_agent",
    model=MODEL,
    instruction=_SEQ_INSIGHT_PROMPT,
    description="Researches topics described in the `campaign_guide`",
    tools=[
        query_web,
        call_insights_generation_agent,
        # AgentTool(agent=insights_generator_agent),
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    after_agent_callback=campaign_callback_function,
)


# insights_generator_agent = Agent(
#     model=MODEL,
#     name="insights_generator_agent",
#     instruction=united_insights_prompt,
#     disallow_transfer_to_parent=True,
#     disallow_transfer_to_peers=True,
#     generate_content_config=json_response_config,
#     output_schema=Insights,
#     output_key="insights",
# )
