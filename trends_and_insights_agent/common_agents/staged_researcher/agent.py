"""Research pipeline — deterministic BaseAgent orchestrator.

ResearchPipelineOrchestrator replaces the old SequentialAgent stack
(combined_research_pipeline + report_saver_agent + research_orchestrator)
with a single BaseAgent that:
  1. Runs each research sub-agent in sequence
  2. Emits rich status messages between stages for GE/frontend
  3. Calls draft_research_report_tool directly (no LLM wrapper) to save the PDF
  4. Supports AE resumability via agent state
"""

from __future__ import annotations

import datetime
import logging

logging.basicConfig(level=logging.INFO)

from typing import AsyncGenerator

from google.genai import types
from google.adk.agents.base_agent import BaseAgent, BaseAgentState
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.tools import google_search
from google.adk.planners import BuiltInPlanner
from google.adk.agents import Agent, ParallelAgent
from google.adk.utils.context_utils import Aclosing
from google.adk.utils.feature_decorator import experimental

import pathlib

from google.adk.tools.skill_toolset import SkillToolset

from trends_and_insights_agent.shared_libraries.config import config
from trends_and_insights_agent.shared_libraries import callbacks, schema_types
from trends_and_insights_agent.skills.skill_loader import load_skill_from_dir

from .tools import recall_prior_insights, draft_research_report_tool

# Load research skill for NovaStorm-evolvable instructions
_research_skill_dir = pathlib.Path(__file__).parent / "../../skills/research"
try:
    _research_skill = load_skill_from_dir(_research_skill_dir)
    _research_skill_toolset = SkillToolset(skills=[_research_skill])
except Exception as _e:
    logging.warning(f"Could not load research skill: {_e}")
    _research_skill_toolset = None
from .sub_agents.campaign_web_researcher.agent import ca_sequential_planner
from .sub_agents.search_web_researcher.agent import gs_sequential_planner
from .sub_agents.youtube_web_researcher.agent import yt_sequential_planner


logger = logging.getLogger("google_adk." + __name__)


# ============================================================
# Sub-agents (unchanged — these are the LLM workers)
# ============================================================

memory_recall_agent = Agent(
    model=config.worker_model,
    name="memory_recall_agent",
    description="Retrieves prior campaign insights from Memory Bank.",
    instruction="""Call `recall_prior_insights` with the brand and product from session state.
    This retrieves historical campaign learnings to enrich the upcoming research refinement.
    Pass the brand from the 'brand' state key and product from the 'target_product' state key.
    After calling the tool, summarize what was retrieved (or note that no prior insights exist).""",
    tools=[recall_prior_insights],
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)

parallel_planner_agent = ParallelAgent(
    name="parallel_planner_agent",
    sub_agents=[yt_sequential_planner, gs_sequential_planner, ca_sequential_planner],
    description="Runs multiple research planning agents in parallel.",
)

merge_planners = Agent(
    name="merge_planners",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    instruction="""You are an AI Assistant responsible for combining initial research findings into a comprehensive summary.
    Your primary task is to organize the following research summaries, clearly attributing findings to their source areas.
    Structure your response using headings for each topic. Ensure the report is coherent and integrates the key points smoothly.

    ---
    **Output Format:**

    # Summary of Campaign and Trend Research

    ## Campaign Guide
    {campaign_web_search_insights}

    ## Search Trend
    {gs_web_search_insights}

    ## YouTube Trends Findings
    {yt_web_search_insights}

    Output *only* the structured report following this format. Do not include introductory or concluding phrases outside this structure, and strictly adhere to using only the provided input summary content.
    """,
    output_key="combined_web_search_insights",
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)

combined_web_evaluator = Agent(
    model=config.critic_model,
    name="combined_web_evaluator",
    description="Critically evaluates research about the campaign guide and generates follow-up queries.",
    instruction=f"""
    You are a meticulous quality assurance analyst evaluating the research findings in 'combined_web_search_insights'.

    Be critical of the completeness of the research.
    Consider the bigger picture and the intersection of the `target_product` and `target_audience`.
    Consider the trends in each of the 'target_search_trends' and 'target_yt_trends' state keys.

    Look for any gaps in depth or coverage, as well as any areas that need more clarification.
        - If you find significant gaps in depth or coverage, write a detailed comment about what's missing, and generate 5-7 specific follow-up queries to fill those gaps.
        - If you don't find any significant gaps, write a detailed comment about any aspect of the campaign guide or trends to research further. Provide 5-7 related queries.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'CampaignFeedback' schema.
    """,
    output_schema=schema_types.CampaignFeedback,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="combined_research_evaluation",
    before_model_callback=[callbacks.before_model_status_callback, callbacks.rate_limit_callback],
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)

enhanced_combined_searcher = Agent(
    model=config.worker_model,
    name="enhanced_combined_searcher",
    description="Executes follow-up searches and integrates new findings.",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    instruction="""
    You are a specialist researcher executing a refinement pass.
    You are tasked to conduct a second round of web research and gather insights related to the trending YouTube video, the trending Search terms, the target audience, and the target product.

    1.  Review the 'combined_research_evaluation' state key to understand the previous round of research.
    2.  Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    3.  Synthesize the new findings and COMBINE them with the existing information in 'combined_web_search_insights'.
    4.  If 'prior_campaign_insights' exists in session state, incorporate relevant learnings into your synthesis (e.g., what messaging worked before, audience preferences, successful creative approaches).
    5.  Your output MUST be the new, complete, and improved set of research insights for the trending Search terms, trending YouTube video, and campaign guide.
    """,
    tools=[google_search],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="combined_web_search_insights",
    after_agent_callback=callbacks.collect_research_sources_callback,
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)

_report_tools = [_research_skill_toolset] if _research_skill_toolset else []

combined_report_composer = Agent(
    model=config.critic_model,
    name="combined_report_composer",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    include_contents="none",
    tools=_report_tools,
    description="Transforms research data and a markdown outline into a final, cited report.",
    instruction="""
    Transform the provided data into a polished, professional, and meticulously cited research report.

    ---
    **INPUT DATA**

    *   **Search Trends:**
        {target_search_trends}

    *   **YouTube Trends:**
        {target_yt_trends}

    *   **YouTube Video Analysis:**
        {yt_video_analysis}

    *   **Final Research:**
        {combined_web_search_insights}

    *   **Citation Sources:**
        `{sources}`

    *   **Prior Campaign Insights (from Memory Bank):**
        {prior_campaign_insights}

    ---
    **CRITICAL: Citation System**
    To cite a source, you MUST insert a special citation tag directly after the claim it supports.

    **The only correct format is:** `<cite source="src-ID_NUMBER" />`

    ---
    **OUTPUT FORMAT**
    Organize the output to include these sections:
    *   **Campaign Guide**
    *   **Search Trend**
    *   **YouTube Trend**
    *   **Key Insights from Research**

    You can use any format you prefer, but here's a suggested structure:
    # Campaign Title
    ## Section Name
    An overview of what this section covers, including specific insights from web research.
    Feel free to add subsections or bullet points if needed to better organize the content.
    Make sure your outline is clear and easy to follow.

    ---
    **Final Instructions**
    Generate a comprehensive report using ONLY the `<cite source="src-ID_NUMBER" />` tag system for all citations.
    Ensure the final report follows a structure similar to the one proposed in the **OUTPUT FORMAT**
    Do not include a "References" or "Sources" section; all citations must be in-line.
    """,
    output_key="combined_final_cited_report",
    after_agent_callback=callbacks.citation_replacement_callback,
    before_model_callback=[callbacks.before_model_status_callback, callbacks.rate_limit_callback],
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)


# ============================================================
# ResearchPipelineOrchestrator — deterministic BaseAgent
# ============================================================

# Pipeline stages in order. Each maps to a sub-agent name except SAVE_REPORT.
RESEARCH_STAGES = [
    ("PARALLEL_RESEARCH", "parallel_planner_agent", "Running parallel research (YouTube, Search, Campaign)..."),
    ("MERGE_INSIGHTS", "merge_planners", "Merging research findings into unified summary..."),
    ("EVALUATE", "combined_web_evaluator", "Evaluating research quality and identifying gaps..."),
    ("MEMORY_RECALL", "memory_recall_agent", "Retrieving prior campaign insights from Memory Bank..."),
    ("ENHANCED_SEARCH", "enhanced_combined_searcher", "Conducting follow-up research to fill gaps..."),
    ("COMPOSE_REPORT", "combined_report_composer", "Composing final cited research report..."),
    ("SAVE_REPORT", None, "Saving research report as PDF..."),
]


@experimental
class ResearchPipelineState(BaseAgentState):
    """Persisted state for AE resumability."""
    current_stage_index: int = 0


class ResearchPipelineOrchestrator(BaseAgent):
    """Deterministic orchestrator for the research pipeline.

    Runs each research sub-agent in sequence with status messages between stages.
    After the report is composed, calls draft_research_report_tool directly
    (no LLM wrapper needed). Supports AE resumability.
    """

    def _determine_start_index(self, ctx: InvocationContext) -> int:
        """Determine which stage to start from based on session state keys.

        On AE, each stream_query is a separate invocation — BaseAgentState
        doesn't persist across invocations. Instead, check session state
        output keys to determine what already completed.
        """
        state = ctx.session.state

        # Check outputs from each stage to determine where to resume
        # COMPOSE_REPORT produces combined_final_cited_report
        report = state.get("combined_final_cited_report", "")
        if report and len(str(report)) > 200:
            # Report already composed — go to SAVE_REPORT
            return 6  # SAVE_REPORT index

        # ENHANCED_SEARCH writes back to combined_web_search_insights (enriched)
        # and combined_research_evaluation exists
        eval_result = state.get("combined_research_evaluation", "")
        insights = state.get("combined_web_search_insights", "")
        prior = state.get("prior_campaign_insights", "")

        if eval_result and insights and prior:
            # Memory recall and enhanced search done — compose report
            return 5  # COMPOSE_REPORT index

        if eval_result and insights:
            # Eval done, need memory recall
            return 3  # MEMORY_RECALL index

        if insights and len(str(insights)) > 200:
            # Merge done, need evaluation
            return 2  # EVALUATE index

        # Check if any parallel research ran (sub-search insights populated)
        gs_insights = state.get("gs_web_search_insights", "")
        yt_insights = state.get("yt_web_search_insights", "")
        ca_insights = state.get("campaign_web_search_insights", "")
        if gs_insights or yt_insights or ca_insights:
            # Parallel research started/done — go to merge
            return 1  # MERGE_INSIGHTS index

        return 0  # Start from beginning

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self.sub_agents:
            return

        # Determine start index from session state (works across AE invocations)
        start_index = self._determine_start_index(ctx)
        logger.info(f"[ResearchPipeline] Starting from stage index {start_index} (of {len(RESEARCH_STAGES)})")

        pause_invocation = False

        for i in range(start_index, len(RESEARCH_STAGES)):
            stage_name, agent_name, status_msg = RESEARCH_STAGES[i]

            # Persist current stage for AE resume
            if ctx.is_resumable:
                state = ResearchPipelineState(current_stage_index=i)
                ctx.set_agent_state(self.name, agent_state=state)
                yield self._create_agent_state_event(ctx)

            # Emit status message
            yield self._status_event(ctx, status_msg)

            if stage_name == "SAVE_REPORT":
                # Direct tool call — no LLM agent needed
                async for event in self._save_report(ctx):
                    yield event
            else:
                # Run the sub-agent
                target = self._get_sub_agent(agent_name)
                if target:
                    async with Aclosing(target.run_async(ctx)) as agen:
                        async for event in agen:
                            yield event
                            if ctx.should_pause_invocation(event):
                                pause_invocation = True

                    if pause_invocation:
                        return

        # Mark complete
        if ctx.is_resumable:
            ctx.set_agent_state(self.name, end_of_agent=True)
            yield self._create_agent_state_event(ctx)

    async def _save_report(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Call draft_research_report_tool directly — no LLM needed."""
        state = ctx.session.state
        processed_report = state.get("research_report_with_citations", "") or state.get("final_report_with_citations", "")
        gcs_folder = state.get("gcs_folder", "")

        if not processed_report:
            yield self._status_event(ctx, "No report to save — skipping PDF generation.")
            return

        # Build save_artifact_fn if artifact_service is available
        save_artifact_fn = None
        if ctx.artifact_service:
            async def _save(filename, artifact_part):
                return await ctx.artifact_service.save_artifact(
                    app_name=ctx.app_name,
                    user_id=ctx.user_id,
                    session_id=ctx.session.id,
                    filename=filename,
                    artifact=artifact_part,
                )
            save_artifact_fn = _save

        result = await draft_research_report_tool(
            processed_report=processed_report,
            gcs_folder=gcs_folder,
            save_artifact_fn=save_artifact_fn,
        )

        status = result.get("status", "failed")
        artifact_key = result.get("artifact_key", "")
        if status == "ok":
            msg = f"Research report saved as PDF: {artifact_key}"
        else:
            msg = f"Failed to save research report: {result.get('error', 'unknown')}"

        yield self._status_event(ctx, msg)

    def _get_sub_agent(self, name: str):
        for agent in self.sub_agents:
            if agent.name == name:
                return agent
        return None

    def _status_event(self, ctx: InvocationContext, message: str) -> Event:
        """Create an event with a status message and ui:status_update."""
        logger.info(f"[ResearchPipeline] {message}")
        event = Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part(text=message)],
            ),
        )
        # Set ui:status_update for GE status chips
        event.actions.state_delta["ui:status_update"] = message
        return event


# ============================================================
# Exported orchestrator
# ============================================================

research_orchestrator = ResearchPipelineOrchestrator(
    name="research_orchestrator",
    description="Orchestrate comprehensive research for the campaign metadata and trending topics.",
    sub_agents=[
        parallel_planner_agent,
        merge_planners,
        combined_web_evaluator,
        memory_recall_agent,
        enhanced_combined_searcher,
        combined_report_composer,
    ],
    after_agent_callback=[
        callbacks.save_research_to_memory,
        callbacks.after_agent_skill_reflection,
    ],
)
