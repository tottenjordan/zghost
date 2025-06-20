import os
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent

# from google.adk.agents.llm_agent import LlmAgent
# from google.adk.tools.agent_tool import AgentTool

# from ...shared_libraries.schema_types import json_response_config
from ...shared_libraries import callbacks
from ...utils import MODEL
from ...tools import (
    query_web,
    call_insights_generation_agent,
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
4. For each insight gathered in the previous steps, use the `call_insights_generation_agent` tool to update the list of structured `insights` in the session state.

"""

campaign_researcher_agent = Agent(
    name="campaign_researcher_agent",
    model=MODEL,
    instruction=_SEQ_INSIGHT_PROMPT,
    description="Researches topics described in the `campaign_guide`",
    tools=[
        query_web,
        call_insights_generation_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    after_agent_callback=callbacks.campaign_callback_function,
)
