from google.genai import types
from google.adk.agents import Agent

# from google.adk.tools import load_artifacts

from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.staged_researcher.agent import combined_research_pipeline
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from google.adk.tools.agent_tool import AgentTool
from .common_agents.staged_researcher.tools import save_draft_report_artifact

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import (
    GLOBAL_INSTR,
    v3_ROOT_AGENT_INSTR,
)

root_agent = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant using the services of multiple sub-agents.",
    instruction=v3_ROOT_AGENT_INSTR,
    global_instruction=GLOBAL_INSTR,
    sub_agents=[
        trends_and_insights_agent,
        ad_content_generator_agent,
        # combined_research_pipeline,
    ],
    tools=[save_draft_report_artifact, AgentTool(agent=combined_research_pipeline)],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks._load_session_state,
    ],
    before_model_callback=callbacks.rate_limit_callback,
)