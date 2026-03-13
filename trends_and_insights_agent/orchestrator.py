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

STAGES = ["TRENDS", "RESEARCH", "CREATIVE", "FOCUS_GROUP", "SAVE_REPORT", "COMPLETE"]

MAX_CREATIVE_ATTEMPTS = 5  # Max times to re-enter CREATIVE before skipping to FOCUS_GROUP

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

        # Stage 2: Need ad creatives AND commercial
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(img_keys, dict):
            img_keys = img_keys.get("img_artifact_keys", [])
        creative_attempts = state.get("_creative_pipeline_attempts", 0)
        creative_exhausted = creative_attempts >= MAX_CREATIVE_ATTEMPTS

        if not img_keys or len(img_keys) < 2:
            if not creative_exhausted:
                return "CREATIVE"
        if not state.get("commercial_artifact") and not creative_exhausted:
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
            state["final_report_with_citations"] = processed_report
            msg = f"Final campaign report saved as PDF: {artifact_key}"
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
