import logging

logging.basicConfig(level=logging.INFO)

from google.adk.tools import LongRunningFunctionTool
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent

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
