import logging

logging.basicConfig(level=logging.INFO)

from google.genai import types
from google.adk.tools import LongRunningFunctionTool
from google.adk.agents import Agent, LlmAgent, SequentialAgent, ParallelAgent

from .tools import save_final_report_artifact
from ...common_agents.auto_researcher.agent import combined_research_pipeline
from ...utils import MODEL


stage_1_report_agent = LlmAgent(
    name="stage_1_report_agent",
    model=MODEL,
    description="Combines research findings into a report and saves it as an artifact.",
    instruction="""You are an AI Assistant responsible for combining research findings into a structured report.

    ### Instructions
    1. Use the `save_final_report_artifact` tool to save the research report as an artifact. Only use this tool once.
    2. Once Step 1 is complete, transfer to the `ad_content_generator_agent` agent.
    """,
    tools=[
        # LongRunningFunctionTool(save_final_report_artifact),
        save_final_report_artifact,
    ],
)


stage_1_research_merger = SequentialAgent(
    name="stage_1_research_merger",
    sub_agents=[combined_research_pipeline, stage_1_report_agent],
    description="Coordinates research pipeline and synthesizes the results.",
)


# # Main orchestrator agent
# stage_1_research_merger = Agent(
#     model="gemini-2.5-pro",
#     name="stage_1_research_merger",
#     description="Orchestrate comprehensive research for the campaign guide and trending topics.",
#     instruction="""**Role:** You are the orchestrator for a comprehensive research workflow.
#     **Objective:** Coordinate the use subagents and tools to conduct research and save the results as an artifact.

#     **Workflow:**
#     1. First, call the `combined_research_pipeline` subagent to conduct web research on the campaign guide and selected trends.
#     2. Once the research tasks are complete, use the `save_final_report_artifact` tool to save the research report as an artifact.
#     3. Transfer back to the `root_agent`.
#     """,
#     sub_agents=[combined_research_pipeline],
#     tools=[save_final_report_artifact],
#     generate_content_config=types.GenerateContentConfig(temperature=1.0),
# )
