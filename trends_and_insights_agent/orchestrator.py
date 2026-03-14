"""CampaignOrchestrator — deterministic state-machine orchestrator for the campaign pipeline.

Replaces the LLM root_agent with a BaseAgent that checks session state keys
to decide which pipeline stage to run next. No LLM decision-making at the top level.

Pipeline stages:
  TRENDS      -> trends_and_insights_agent
  RESEARCH    -> research_orchestrator
  CREATIVE    -> creative_production_orchestrator (ad creative + AV studio + QA)
  FOCUS_GROUP -> focus_group_evaluator_agent
  SAVE_REPORT -> save_final_report_tool (direct call, no LLM)
  COMPLETE    -> done
"""

from __future__ import annotations

import logging
import os
from typing import AsyncGenerator

from google.genai import types
from google.adk.agents.base_agent import BaseAgent, BaseAgentState
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing
from google.adk.utils.feature_decorator import experimental

from .common_agents.ad_content_generator.tools import save_final_report_tool
from .shared_libraries.skill_evolution import run_skill_council

logger = logging.getLogger("google_adk." + __name__)


def _parse_search_trends(gtrends_result: dict) -> list[dict]:
    """Parse ALL search trends from get_daily_gtrends() markdown table output.

    Returns list of dicts with trend_title, trend_rank, trend_refresh_date.
    """
    if gtrends_result.get("status") != "ok":
        return []
    md_table = gtrends_result.get("markdown_table", "")
    if not md_table:
        return []
    # Markdown table format (from pandas to_markdown with index=True):
    #   |    | term   |   rank | refresh_date   |
    #   |---:|:-------|-------:|:---------------|
    #   |  1 | topic  |      1 | 2026-03-10     |
    lines = [l.strip() for l in md_table.strip().split("\n") if l.strip()]
    # Skip header (line 0) and separator (line 1), parse all data rows
    if len(lines) < 3:
        return []

    trends = []
    for row in lines[2:]:  # All rows after header and separator
        cells = [c.strip() for c in row.split("|") if c.strip()]
        # cells: [index, term, rank, refresh_date]
        if len(cells) < 4:
            continue
        # Convert YYYY-MM-DD to MM/DD/YYYY if needed (downstream expects MM/DD/YYYY)
        date_str = str(cells[3])
        if len(date_str) == 10 and date_str[4] == "-":
            parts = date_str.split("-")
            date_str = f"{parts[1]}/{parts[2]}/{parts[0]}"
        trends.append({
            "trend_title": cells[1],
            "trend_rank": int(cells[2]),
            "trend_refresh_date": date_str,
        })
    return trends


def _parse_top_search_trend(gtrends_result: dict) -> dict | None:
    """Parse the #1 search trend from get_daily_gtrends() markdown table output.

    Returns dict with trend_title, trend_rank, trend_refresh_date or None.
    Kept for backward compatibility.
    """
    trends = _parse_search_trends(gtrends_result)
    return trends[0] if trends else None

STAGES = ["TRENDS", "RESEARCH", "CREATIVE", "FOCUS_GROUP", "SAVE_REPORT", "COMPLETE"]

MAX_CREATIVE_ATTEMPTS = 15  # Max times to re-enter CREATIVE before skipping to FOCUS_GROUP

STAGE_STATUS_MESSAGES = {
    "TRENDS": "Gathering campaign metadata and trend selections...",
    "RESEARCH": "Running market research pipeline...",
    "CREATIVE": "Running creative production pipeline (ad copy, visuals, commercial)...",
    "FOCUS_GROUP": "Running focus group evaluation...",
    "SAVE_REPORT": "Generating final campaign report PDF...",
    "COMPLETE": "Campaign pipeline complete!",
}

STAGE_AGENT_MAP = {
    "TRENDS": "trends_and_insights_agent",
    "RESEARCH": "research_orchestrator",
    "CREATIVE": "creative_production_orchestrator",
    "FOCUS_GROUP": "focus_group_evaluator_agent",
    # SAVE_REPORT is handled directly (no agent)
}


@experimental
class CampaignOrchestratorState(BaseAgentState):
    """Persisted state for resumability on Agent Engine."""
    current_stage: str = "INIT"


class CampaignOrchestrator(BaseAgent):
    """Deterministic state-machine orchestrator for the campaign pipeline.

    Checks session state keys to determine which stage completed and runs the
    next one. Supports resumability on Agent Engine via agent state persistence.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        stage = self._determine_stage(ctx)
        state = ctx.session.state

        # Track creative pipeline attempts to break infinite loops
        # Counter is persisted via event state_delta (not direct state mutation)
        if stage == "CREATIVE":
            creative_attempts = state.get("_creative_pipeline_attempts", 0) + 1
            if creative_attempts > MAX_CREATIVE_ATTEMPTS:
                logger.warning(
                    f"[CampaignOrchestrator] Creative pipeline exhausted "
                    f"({creative_attempts} attempts). Skipping to FOCUS_GROUP."
                )
                stage = "FOCUS_GROUP"
            else:
                # Persist counter via state_delta event
                counter_event = self._status_event(
                    ctx, f"Creative pipeline attempt {creative_attempts}/{MAX_CREATIVE_ATTEMPTS}..."
                )
                counter_event.actions.state_delta["_creative_pipeline_attempts"] = creative_attempts
                yield counter_event

        logger.info(f"[CampaignOrchestrator] Determined stage: {stage}")

        # Persist stage for AE resumability
        if ctx.is_resumable:
            agent_state = CampaignOrchestratorState(current_stage=stage)
            ctx.set_agent_state(self.name, agent_state=agent_state)
            yield self._create_agent_state_event(ctx)

        if stage == "COMPLETE":
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Campaign pipeline complete! All stages finished successfully.")],
                ),
            )
            if ctx.is_resumable:
                ctx.set_agent_state(self.name, end_of_agent=True)
                yield self._create_agent_state_event(ctx)
            return

        # Emit status message
        status_msg = STAGE_STATUS_MESSAGES.get(stage, f"Running stage: {stage}")
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part(text=status_msg)],
            ),
        )

        if stage == "SAVE_REPORT":
            # Direct tool call — no LLM needed
            async for event in self._save_final_report(ctx):
                yield event
        elif stage == "TRENDS" and state.get("autopilot_mode"):
            # Deterministic trend gathering — no LLM needed
            async for event in self._gather_trends_deterministic(ctx):
                yield event
        else:
            # Route to the sub-agent for this stage
            target = self._get_agent_for_stage(stage)
            if target:
                async with Aclosing(target.run_async(ctx)) as agen:
                    async for event in agen:
                        yield event
                        if ctx.should_pause_invocation(event):
                            return

        # After sub-agent completes, mark end for AE
        if ctx.is_resumable:
            ctx.set_agent_state(self.name, end_of_agent=True)
            yield self._create_agent_state_event(ctx)

    def _determine_stage(self, ctx: InvocationContext) -> str:
        """Check session state keys to determine which stage to run next."""
        state = ctx.session.state

        # Stage 0: Need trends
        search_trends = state.get("target_search_trends")
        yt_trends = state.get("target_yt_trends")
        if not self._has_trends(search_trends) or not self._has_trends(yt_trends):
            return "TRENDS"

        # Stage 1: Need research report
        report = state.get("combined_final_cited_report", "")
        if not report or len(str(report)) < 500:
            return "RESEARCH"

        # Stage 2: Need commercial (images are optional)
        creative_attempts = state.get("_creative_pipeline_attempts", 0)
        creative_exhausted = creative_attempts >= MAX_CREATIVE_ATTEMPTS
        has_commercial = bool(state.get("commercial_artifact"))

        if not has_commercial and not creative_exhausted:
            return "CREATIVE"

        # Stage 3: Need focus group evaluation
        if not state.get("focus_group_evaluation"):
            return "FOCUS_GROUP"

        # Stage 4: Need final report PDF
        if not state.get("final_report_with_citations"):
            return "SAVE_REPORT"

        return "COMPLETE"

    def _has_trends(self, trends) -> bool:
        """Check if trends state key has actual trend data."""
        if not trends:
            return False
        if isinstance(trends, dict):
            for v in trends.values():
                if isinstance(v, list) and len(v) > 0:
                    return True
            return False
        if isinstance(trends, list):
            return len(trends) > 0
        return bool(trends)

    def _get_agent_for_stage(self, stage: str):
        """Look up the sub-agent for a given stage."""
        agent_name = STAGE_AGENT_MAP.get(stage)
        if not agent_name:
            return None
        agent_map = {a.name: a for a in self.sub_agents}
        return agent_map.get(agent_name)

    async def _gather_trends_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Deterministic trend selection for autopilot mode — no LLM needed.

        Fetches Google Search trends and YouTube trends directly, auto-selects
        the #1 ranked items, and persists them via state_delta.
        """
        from .common_agents.trend_assistant.tools import get_daily_gtrends, get_youtube_trends

        state = ctx.session.state
        yield self._status_event(ctx, "Autopilot: gathering trends deterministically...")

        # --- Persist campaign metadata via state_delta ---
        metadata_delta = {}
        for key in ("brand", "target_product", "target_audience", "key_selling_points"):
            val = state.get(key, "")
            if val:
                metadata_delta[key] = val
        if metadata_delta:
            meta_event = self._status_event(ctx, f"Campaign metadata: {', '.join(metadata_delta.keys())}")
            meta_event.actions.state_delta.update(metadata_delta)
            yield meta_event

        # --- Fetch and score Google Search Trends ---
        try:
            gtrends_result = get_daily_gtrends()
            all_trends = _parse_search_trends(gtrends_result)
            if all_trends:
                # Build keyword set from brand, product, and selling points
                brand = state.get("brand", "").lower()
                product = state.get("target_product", "").lower()
                selling_points = state.get("key_selling_points", "").lower()
                keywords = set()
                for text in [brand, product, selling_points]:
                    keywords.update(word.strip() for word in text.split() if len(word.strip()) > 3)

                # Score each trend by keyword overlap
                best_trend = None
                best_score = -1
                best_rationale = ""

                for trend in all_trends:
                    trend_title_lower = trend["trend_title"].lower()
                    score = sum(1 for kw in keywords if kw in trend_title_lower)

                    if score > best_score or (score == best_score and trend["trend_rank"] < all_trends[0]["trend_rank"]):
                        best_trend = trend
                        best_score = score
                        if score > 0:
                            matched_kw = [kw for kw in keywords if kw in trend_title_lower]
                            best_rationale = f"Keyword match: {', '.join(matched_kw[:3])}"
                        else:
                            best_rationale = f"Default to rank #{trend['trend_rank']} (no keyword overlap)"

                # If no keyword overlap at all, fall back to rank #1
                if best_score == 0:
                    best_trend = all_trends[0]
                    best_rationale = "No keyword overlap — using rank #1 trend"

                search_delta = {"target_search_trends": [best_trend]}
                trend_event = self._status_event(
                    ctx, f"Auto-selected search trend: \"{best_trend['trend_title']}\" (rank {best_trend['trend_rank']}) — {best_rationale}"
                )
                trend_event.actions.state_delta["target_search_trends"] = search_delta
                trend_event.actions.state_delta["trend_relevance_rationale"] = best_rationale
                yield trend_event
            else:
                yield self._status_event(ctx, "Warning: Could not parse search trends. Pipeline may retry.")
        except Exception as e:
            logger.warning(f"[CampaignOrchestrator] Failed to fetch search trends: {e}")
            yield self._status_event(ctx, f"Warning: Search trends fetch failed: {e}")

        # --- Fetch and auto-select YouTube Trends ---
        try:
            yt_result = get_youtube_trends()
            # yt_result format: {"row_1": {"videoId": ..., "videoTitle": ..., "duration": ..., "videoURL": ...}, ...}
            first_key = next(iter(yt_result), None)
            if first_key:
                first_video = yt_result[first_key]
                yt_selection = {
                    "video_title": first_video.get("videoTitle", ""),
                    "video_duration": first_video.get("duration", ""),
                    "video_url": first_video.get("videoURL", ""),
                }
                yt_delta = {"target_yt_trends": [yt_selection]}
                yt_event = self._status_event(
                    ctx, f"Auto-selected YouTube trend: \"{yt_selection['video_title']}\""
                )
                yt_event.actions.state_delta["target_yt_trends"] = yt_delta
                yield yt_event
            else:
                yield self._status_event(ctx, "Warning: No YouTube trends returned. Pipeline may retry.")
        except Exception as e:
            logger.warning(f"[CampaignOrchestrator] Failed to fetch YouTube trends: {e}")
            yield self._status_event(ctx, f"Warning: YouTube trends fetch failed: {e}")

        yield self._status_event(ctx, "Trend selection complete. Proceeding to research...")

    async def _save_final_report(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Call save_final_report_tool directly — no LLM needed.

        Also runs the NovaStorm Skill Council if enabled, so skills
        discuss each other's handoffs and store cross-skill recommendations.
        """
        state = ctx.session.state
        processed_report = state.get("combined_final_cited_report", "")
        gcs_folder = state.get("gcs_folder", "")

        # Run Skill Council — all skills discuss and improve each other
        novastorm_enabled = (
            os.environ.get("NOVASTORM_ENABLED", "").lower() == "true"
            or state.get("novastorm_enabled", False)
        )
        if novastorm_enabled:
            yield self._status_event(ctx, "Running Skill Council — skills discussing pipeline improvements...")
            try:
                user_id = ctx.user_id or "default"
                council_result = run_skill_council(dict(state), user_id)
                state["skill_council_result"] = council_result
                pipeline_score = council_result.get("pipeline_score", 0)
                top = council_result.get("top_improvements", [])
                summary = f"Skill Council complete: pipeline score {pipeline_score}/10."
                if top:
                    summary += f" Top priority: {top[0][:80]}"
                yield self._status_event(ctx, summary)
            except Exception as e:
                logger.warning(f"[NovaStorm] Skill Council failed (non-fatal): {e}")

        if not processed_report:
            yield self._status_event(ctx, "No research report to save — skipping PDF generation.")
            return

        # Extract artifact lists
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(img_keys, dict):
            img_artifact_list = img_keys.get("img_artifact_keys", [])
        else:
            img_artifact_list = img_keys if isinstance(img_keys, list) else []

        vid_keys = state.get("vid_artifact_keys", {})
        if isinstance(vid_keys, dict):
            vid_artifact_list = vid_keys.get("vid_artifact_keys", [])
        else:
            vid_artifact_list = vid_keys if isinstance(vid_keys, list) else []

        commercial_artifact = state.get("commercial_artifact", {})
        focus_group_evaluation = state.get("focus_group_evaluation", "")
        focus_group_panelists = state.get("focus_group_panelists", {})

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

        result = await save_final_report_tool(
            processed_report=processed_report,
            img_artifact_list=img_artifact_list,
            vid_artifact_list=vid_artifact_list,
            commercial_artifact=commercial_artifact,
            focus_group_evaluation=focus_group_evaluation,
            focus_group_panelists=focus_group_panelists,
            gcs_folder=gcs_folder,
            save_artifact_fn=save_artifact_fn,
        )

        status = result.get("status", "failed")
        artifact_key = result.get("artifact_key", "")
        if status == "ok":
            # Persist via state_delta event (direct mutation doesn't survive AE invocations)
            report_event = self._status_event(
                ctx, f"Final campaign report saved as PDF: {artifact_key}"
            )
            report_event.actions.state_delta["final_report_with_citations"] = processed_report
            yield report_event
        else:
            msg = f"Failed to save final report: {result.get('error', 'unknown')}"
            yield self._status_event(ctx, msg)

    def _status_event(self, ctx: InvocationContext, message: str) -> Event:
        """Create an event with a status message and ui:status_update."""
        logger.info(f"[CampaignOrchestrator] {message}")
        event = Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part(text=message)],
            ),
        )
        event.actions.state_delta["ui:status_update"] = message
        return event
