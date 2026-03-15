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
import os

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

class RecallMemoryDeterministic:
    """Helper class to recall prior insights deterministically."""

    def __init__(self, name: str = "RecallMemoryDeterministic", agent_engine_id: str | None = None):
        """Initialize with agent_engine_id.

        Args:
            name: The name of the helper (used for author in events).
            agent_engine_id: Optional. Default to env variable MEMORY_BANK_AGENT_ENGINE_ID.
        """
        self.name = name
        self.agent_engine_id = agent_engine_id or os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
        import logging
        self.logger = logging.getLogger(__name__)

    def _status_event(self, ctx: InvocationContext, message: str) -> Event:
        """Create an event with a status message and ui:status_update."""
        self.logger.info(f"[{self.name}] {message}")
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

    async def run(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Recall prior campaign insights deterministically — no LLM needed.

        Args:
            ctx: The invocation context.

        Yields:
            Status events.
        """
        import os
        state = ctx.session.state
        brand = state.get("brand", "")
        product = state.get("target_product", "")

        if not brand and not product:
            event = self._status_event(ctx, "No brand/product set — skipping memory recall.")
            event.actions.state_delta["prior_campaign_insights"] = ""
            event.actions.state_delta["_memory_recall_done"] = True
            yield event
            return

        try:
            if not self.agent_engine_id:
                event = self._status_event(ctx, "Memory Bank not configured — skipping recall")
                event.actions.state_delta["prior_campaign_insights"] = ""
                event.actions.state_delta["_memory_recall_done"] = True
                yield event
                return

            import vertexai
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            project_number = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
            location = os.getenv("MEMORY_BANK_LOCATION", "us-central1")

            client = vertexai.Client(project=project, location=location)
            resource_name = f"projects/{project_number}/locations/{location}/reasoningEngines/{self.agent_engine_id}"

            search_query = (
                f"Campaign insights for {brand} {product}. "
                f"What messaging worked, audience reactions, creative strategies."
            )

            results = list(client.agent_engines.memories.retrieve(
                name=resource_name,
                scope={"user_id": ctx.user_id or "default", "memory_type": "campaign_insight"},
                similarity_search_params={
                    "search_query": search_query,
                    "top_k": 5,
                },
            ))

            # Also query skill memories
            skill_results = list(client.agent_engines.memories.retrieve(
                name=resource_name,
                scope={"user_id": ctx.user_id or "default", "memory_type": "skill_memory", "skill": "research"},
                similarity_search_params={
                    "search_query": f"Research techniques and patterns for {brand} {product}",
                    "top_k": 5,
                },
            ))
            results.extend(skill_results)

            insights = []
            for result in results:
                fact = getattr(getattr(result, "memory", None), "fact", None)
                if not fact:
                    fact = str(result)
                insights.append(fact)

            if insights:
                prior_text = "\n- ".join([""] + insights)
                event = self._status_event(ctx, f"Retrieved {len(insights)} prior campaign insights from Memory Bank")
                event.actions.state_delta["prior_campaign_insights"] = prior_text
                event.actions.state_delta["_memory_recall_done"] = True
                yield event
            else:
                event = self._status_event(ctx, "No prior campaign insights found in Memory Bank")
                event.actions.state_delta["prior_campaign_insights"] = ""
                event.actions.state_delta["_memory_recall_done"] = True
                yield event

        except Exception as e:
            self.logger.warning(f"[{self.name}] Memory recall failed (non-fatal): {e}")
            event = self._status_event(ctx, f"Memory recall failed (non-fatal): {str(e)[:80]}")
            event.actions.state_delta["prior_campaign_insights"] = ""
            event.actions.state_delta["_memory_recall_done"] = True
            yield event


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

        # If research pipeline already completed, signal end-of-agent
        if state.get("_research_pipeline_complete"):
            return len(RESEARCH_STAGES)  # Past all stages — triggers end_of_agent

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

        memory_done = state.get("_memory_recall_done", False)
        if eval_result and insights and (prior or memory_done):
            # Memory recall done — proceed to enhanced search
            return 4  # ENHANCED_SEARCH index

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

        # Already complete — mark end_of_agent immediately
        if start_index >= len(RESEARCH_STAGES):
            logger.info("[ResearchPipeline] Already complete — ending agent")
            if ctx.is_resumable:
                ctx.set_agent_state(self.name, end_of_agent=True)
                yield self._create_agent_state_event(ctx)
            return

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
                # Mark research pipeline complete so _determine_start_index
                # doesn't loop back to SAVE_REPORT on next AE wave
                done_event = self._status_event(ctx, "Research pipeline complete.")
                done_event.actions.state_delta["_research_pipeline_complete"] = True
                yield done_event
            elif stage_name == "MERGE_INSIGHTS":
                # Deterministic merge — no LLM needed, just concatenate
                async for event in self._merge_insights_deterministic(ctx):
                    yield event
            elif stage_name == "MEMORY_RECALL":
                # Deterministic memory recall — no LLM agent needed
                async for event in self._recall_memory_deterministic(ctx):
                    yield event
            elif stage_name == "PARALLEL_RESEARCH":
                # Run parallel research with wave-count fallthrough
                session_state = ctx.session.state
                research_waves = session_state.get("_research_parallel_waves", 0) + 1
                wave_event = self._status_event(ctx, f"Parallel research wave {research_waves}/12...")
                wave_event.actions.state_delta["_research_parallel_waves"] = research_waves
                yield wave_event

                MAX_RESEARCH_WAVES = 12
                if research_waves > MAX_RESEARCH_WAVES:
                    # Exceeded budget — run deterministic merge immediately with whatever we have
                    yield self._status_event(ctx, f"Parallel research exceeded {MAX_RESEARCH_WAVES} waves — merging available data")
                    async for event in self._merge_insights_deterministic(ctx):
                        yield event

                    # Always mark research complete to prevent infinite re-entry
                    merged = ctx.session.state.get("combined_web_search_insights", "")

                    # If merge still found nothing, build a rich fallback report
                    if not merged:
                        # Build a rich fallback using any available data (yt_video_analysis is often populated)
                        yt_analysis = session_state.get("yt_video_analysis", "")
                        selling_points = session_state.get("key_selling_points", "N/A")
                        product = session_state.get("target_product", "Unknown")
                        brand = session_state.get("brand", "Unknown")
                        audience = session_state.get("target_audience", "Unknown")
                        search_trends = session_state.get("target_search_trends", "")
                        yt_trends = session_state.get("target_yt_trends", "")

                        # Format trends for the report
                        trend_lines = []
                        if isinstance(search_trends, dict):
                            for t in search_trends.get("target_search_trends", []):
                                trend_lines.append(f"- **{t.get('title', '')}**: {t.get('description', '')}")
                        if isinstance(yt_trends, dict):
                            for t in yt_trends.get("target_yt_trends", []):
                                trend_lines.append(f"- **{t.get('title', '')}**: {t.get('description', '')}")
                        trends_section = "\n".join(trend_lines) if trend_lines else "No trends available."

                        fallback_report = (
                            f"# Market Research Report: {product} by {brand}\n\n"
                            f"## Campaign Brief\n"
                            f"**Product:** {product}\n"
                            f"**Brand:** {brand}\n"
                            f"**Target Audience:** {audience}\n"
                            f"**Key Selling Points:** {selling_points}\n\n"
                            f"## Trend Drivers\n{trends_section}\n\n"
                            f"## YouTube Cultural Intelligence\n{yt_analysis}\n\n"
                            f"## Strategic Recommendations\n"
                            f"Based on the available intelligence, the campaign should:\n"
                            f"1. Lead with the product's unique selling points: {selling_points}\n"
                            f"2. Target {audience} through trend-aligned messaging\n"
                            f"3. Leverage visual and sensory storytelling to convey the brand experience\n"
                        )
                        force_event = self._status_event(ctx, "No research insights persisted — using fallback report to unblock pipeline")
                        force_event.actions.state_delta["combined_web_search_insights"] = fallback_report
                        force_event.actions.state_delta["combined_final_cited_report"] = fallback_report
                        force_event.actions.state_delta["_research_pipeline_complete"] = True
                        yield force_event
                        logger.warning("[ResearchPipeline] Forced fallback report + pipeline complete — output_key state lost on AE")
                    else:
                        # Merge produced data — mark complete and also set as final report
                        done_event = self._status_event(ctx, "Research budget exhausted — proceeding with merged data.")
                        done_event.actions.state_delta["_research_pipeline_complete"] = True
                        if not ctx.session.state.get("combined_final_cited_report") or len(str(ctx.session.state.get("combined_final_cited_report", ""))) < 200:
                            done_event.actions.state_delta["combined_final_cited_report"] = merged
                        yield done_event
                        logger.info("[ResearchPipeline] Merge produced data — pipeline complete")
                    return  # End wave

                target = self._get_sub_agent(agent_name)
                if target:
                    # Collect agent text outputs to persist via state_delta
                    collected_texts = {"gs": [], "yt": [], "ca": []}
                    async with Aclosing(target.run_async(ctx)) as agen:
                        async for event in agen:
                            yield event
                            # Capture text from sub-agent events for state persistence
                            if (hasattr(event, 'content') and event.content
                                    and hasattr(event, 'author') and event.author):
                                for part in (event.content.parts or []):
                                    if hasattr(part, 'text') and part.text and len(part.text) > 50:
                                        author = event.author or ""
                                        if "gs_" in author or "search_web" in author:
                                            collected_texts["gs"].append(part.text)
                                        elif "yt_" in author or "youtube" in author:
                                            collected_texts["yt"].append(part.text)
                                        elif "campaign" in author or "ca_" in author:
                                            collected_texts["ca"].append(part.text)
                            if ctx.should_pause_invocation(event):
                                pause_invocation = True

                    # Persist any collected text via state_delta (output_key doesn't survive AE)
                    delta_event = None
                    if collected_texts["gs"] and not session_state.get("gs_web_search_insights"):
                        delta_event = delta_event or self._status_event(ctx, "Persisting research insights...")
                        delta_event.actions.state_delta["gs_web_search_insights"] = "\n\n".join(collected_texts["gs"])
                    if collected_texts["yt"] and not session_state.get("yt_web_search_insights"):
                        delta_event = delta_event or self._status_event(ctx, "Persisting research insights...")
                        delta_event.actions.state_delta["yt_web_search_insights"] = "\n\n".join(collected_texts["yt"])
                    if collected_texts["ca"] and not session_state.get("campaign_web_search_insights"):
                        delta_event = delta_event or self._status_event(ctx, "Persisting research insights...")
                        delta_event.actions.state_delta["campaign_web_search_insights"] = "\n\n".join(collected_texts["ca"])
                    if delta_event:
                        yield delta_event
                        logger.info(f"[ResearchPipeline] Persisted research via state_delta: gs={len(collected_texts['gs'])} yt={len(collected_texts['yt'])} ca={len(collected_texts['ca'])}")

                    if pause_invocation:
                        return
            else:
                # Run the sub-agent, capturing text output for state_delta persistence
                # (output_key doesn't survive AE wave timeouts)
                target = self._get_sub_agent(agent_name)
                if target:
                    last_text = ""
                    async with Aclosing(target.run_async(ctx)) as agen:
                        async for event in agen:
                            yield event
                            # Capture text for state_delta persistence
                            if hasattr(event, 'content') and event.content:
                                for part in (event.content.parts or []):
                                    if hasattr(part, 'text') and part.text and len(part.text) > 100:
                                        if not getattr(part, 'thought', False):
                                            last_text = part.text
                            if ctx.should_pause_invocation(event):
                                pause_invocation = True

                    # Persist output via state_delta for key stages
                    if last_text and not pause_invocation:
                        session_state = ctx.session.state
                        if stage_name == "COMPOSE_REPORT" and not session_state.get("combined_final_cited_report"):
                            persist_event = self._status_event(ctx, f"Research report composed ({len(last_text)} chars)")
                            persist_event.actions.state_delta["combined_final_cited_report"] = last_text
                            yield persist_event
                            logger.info(f"[ResearchPipeline] Persisted combined_final_cited_report via state_delta: {len(last_text)} chars")
                        elif stage_name == "ENHANCED_SEARCH" and len(last_text) > len(str(session_state.get("combined_web_search_insights", ""))):
                            persist_event = self._status_event(ctx, f"Enhanced research persisted ({len(last_text)} chars)")
                            persist_event.actions.state_delta["combined_web_search_insights"] = last_text
                            yield persist_event
                            logger.info(f"[ResearchPipeline] Persisted enhanced combined_web_search_insights via state_delta: {len(last_text)} chars")

                    if pause_invocation:
                        return

        # Mark complete
        if ctx.is_resumable:
            ctx.set_agent_state(self.name, end_of_agent=True)
            yield self._create_agent_state_event(ctx)

    async def _merge_insights_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Merge parallel research insights deterministically — no LLM needed.

        Concatenates gs/yt/campaign insights into combined_web_search_insights.
        This replaces the LLM-based merge_planners agent which frequently times
        out on AE waves.
        """
        state = ctx.session.state
        gs = state.get("gs_web_search_insights", "")
        yt = state.get("yt_web_search_insights", "")
        ca = state.get("campaign_web_search_insights", "")

        sections = []
        if ca:
            sections.append(f"## Campaign Guide\n{ca}")
        if gs:
            sections.append(f"## Search Trend Analysis\n{gs}")
        if yt:
            sections.append(f"## YouTube Trends Findings\n{yt}")

        if not sections:
            yield self._status_event(ctx, "No parallel research insights found — skipping merge.")
            return

        merged = "# Summary of Campaign and Trend Research\n\n" + "\n\n".join(sections)

        event = self._status_event(ctx, f"Merged {len(sections)} research streams ({len(merged)} chars)")
        event.actions.state_delta["combined_web_search_insights"] = merged
        yield event
        logger.info(f"[ResearchPipeline] Deterministic merge: {len(merged)} chars from {len(sections)} streams")

    async def _recall_memory_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Recall prior campaign insights deterministically — no LLM needed.

        Delegates to RecallMemoryDeterministic helper class.
        """
        recaller = RecallMemoryDeterministic()
        async for event in recaller.run(ctx):
            yield event

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
