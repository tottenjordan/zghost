from google.genai import types

from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from .common_agents.marketing_brief_data_generator.agent import (
    brief_data_generation_agent,
)
from .common_agents.research_generator.agent import (
    research_generation_agent,
)
from .common_agents.idea_generator.agent import create_new_ideas_agent
from .common_agents.trend_assisstant.agent import trends_and_insights_agent
from .common_agents.image_generator.agent import image_generation_agent

from .prompts import root_agent_instructions

# from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import google_search
from google.adk.agents.callback_context import CallbackContext

from google.adk.models import LlmRequest

from .tools import (
    call_brief_generation_agent,
    call_research_generation_agent
)
from typing import Optional

def brief_callback_function(
    callback_context: CallbackContext
) -> Optional[types.Content]:
    
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()
    print(f"\n[Callback] Entering agent: {agent_name} (Inv: {invocation_id})")
    print(f"[Callback] Current State: {current_state}")
    
    # Check the condition in session state dictionary
    marketing_brief = callback_context.state.get("campaign_brief")
    if marketing_brief is None:
        callback_context.state["campaign_brief"] = {"brief": "not yet populated"}
        # return types.Content(
        #     parts=[types.Part(text=f"Agent {agent_name} skipped by before_agent_callback due to state (campaign_brief).")],
        #     role="model" # Assign model role to the overriding response
        # )
    else:
        return None


root_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="marketing_idea_generator_agent",
    instruction=root_agent_instructions,
    global_instruction=(
        f"""
        You are an expert marketing agent developing research-based marketing campaign briefs, enriched by Google Search and YouTube.
        """
    ),
    sub_agents=[
        create_new_ideas_agent,
        image_generation_agent,
        trends_and_insights_agent,
        brief_data_generation_agent,
        research_generation_agent
    ],
    tools=[
        # google_search,
        load_artifacts,
        # call_brief_generation_agent,
        # call_research_generation_agent

    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        # response_modalities=["TEXT", "AUDIO"]
    ),
    before_agent_callback=brief_callback_function,
)
