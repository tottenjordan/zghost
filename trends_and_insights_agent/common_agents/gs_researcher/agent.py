from google.genai import types
from google.adk.agents import Agent

# from google.adk.agents.llm_agent import LlmAgent
# from google.adk.tools.agent_tool import AgentTool

# from ...shared_libraries.types import json_response_config
from ...utils import MODEL, campaign_callback_function
from ...tools import (
    query_web,
    call_search_trends_generator_agent,
)

# Researcher 3: trending Search
_SEQ_GS_TREND_PROMPT = """**Role:** You are a Research Assistant specializing in Search trends.

**Objective:** Your goal is to conduct targeted research to better understand the cultural significance of the trending Search terms. Your research should answer questions like:
*   Why are these search terms trending? Who is involved?
*   Describe any key entities involved (i.e., people, places, organizations, named events, etc.).
*   Describe the relationships between these key entities, especially in the context of the trending topic.
*   Are there any related themes that would resonate with our target audience(s)?
*   Is there any opportunity to connect this trend to our campaign guide?

**Available Tools:** You have access to the following tools:
*   `query_web` : Use this tool to perform web searches with Google Search.
*   `call_search_trends_generator_agent` : Use this tool to update the `search_trends` session state from your web research on trending search topics.

**Instructions:** Follow these steps to complete your objective:
1. For each entry in `target_search_trends`, use the `query_web` tool to perform several Google Searches related to the trend topic.
2. Using the output from the previous step, generate trend context that includes a summary describing what is taking place or being discussed, any key entities involved, etc.
3. For each insight gathered in the previous steps, call the `call_search_trends_generator_agent` tool to store this insight in the `search_trends` session state.

Once these steps are complete, transfer back to the root agent.

"""

gs_researcher_agent = Agent(
    name="gs_researcher_agent",
    model=MODEL,
    instruction=_SEQ_GS_TREND_PROMPT,
    description="Researches trending Search terms selected by the user.",
    tools=[
        query_web,
        call_search_trends_generator_agent,
        # AgentTool(agent=search_trends_generator_agent),
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    after_agent_callback=campaign_callback_function,
)


# search_trends_generator_agent = Agent(
#     model=MODEL,
#     name="search_trends_generator_agent",
#     instruction=search_trends_generation_prompt,
#     disallow_transfer_to_parent=True,
#     disallow_transfer_to_peers=True,
#     generate_content_config=json_response_config,
#     output_schema=Search_Trends,
#     output_key="search_trends",
# )
