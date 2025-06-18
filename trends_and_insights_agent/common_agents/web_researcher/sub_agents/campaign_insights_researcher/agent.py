import os
import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.agents import Agent

# from google.adk.agents.llm_agent import LlmAgent
# from google.adk.tools.agent_tool import AgentTool

# from .....shared_libraries.types import json_response_config
from .....utils import MODEL, campaign_callback_function
from .....tools import (
    query_web,
    call_insights_generation_agent,
)


# # callback function
# def insights_callback_function(
#     callback_context: CallbackContext,
# ) -> Optional[types.Content]:
#     """
#     """
#     agent_name = callback_context.agent_name
#     invocation_id = callback_context.invocation_id
#     current_state = callback_context.state.to_dict()
#     logging.info(f"\n[Callback] Entering agent: {agent_name} (Inv: {invocation_id})")
#     logging.info(f"[Callback] Current State: {current_state}")

#     insights = callback_context.state.get("insights")
#     return_content = None  # placeholder for optional returned parts


# Researcher 1: campaign insights
_SEQ_INSIGHT_PROMPT = """**Role:** You are a Research Assistant specializing in marketing campaign insights.

**Objective:** Your goal is to conduct web research and gather insights related to concepts from the campaign guide. These insights should answer questions like:
*  What's relevant, distinctive, or helpful about the {campaign_guide.target_product} or {campaign_guide.brand}?
*  Which product features would the target audience best resonate with?
*  How could marketers make a culturally relevant advertisement related to product insights?

**Instructions:** Follow these steps to complete the task at hand:
1. Use the `query_web` tool to perform Google Searches for several topics described in the `campaign_guide`.
2. Gvien the results from the previous step, generate insights about the target product and target audience.
3. For each insight, use the `call_insights_generation_agent` tool to update the list of structured `insights` in the session state.
"""

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

campaign_insights_researcher = Agent(
    name="campaign_insights_researcher",
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
