"""CampaignOrchestrator — deterministic state-machine orchestrator for the campaign pipeline.

Replaces the LLM root_agent with a BaseAgent that checks session state keys
to decide which pipeline stage to run next. No LLM decision-making at the top level.

Pipeline stages (flat — no intermediate orchestrators):
  TRENDS      -> deterministic (autopilot) OR interactive trend selection
  RESEARCH    -> research_agent (LLM sub-agent)
  AD_CREATIVE -> ad_creative_agent (LLM sub-agent)
  IMAGE_GEN   -> deterministic SDK (Imagen 4)
  AV_STUDIO   -> deterministic SDK (Veo 3.1)
  FOCUS_GROUP -> focus_group_evaluator_agent (LLM sub-agent)
  SAVE_REPORT -> save_final_report_tool (direct call, no LLM)
  COMPLETE    -> done
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from typing import AsyncGenerator

from google import genai
from google.genai import types
from google.genai.types import GenerateVideosConfig
from google.adk.agents.base_agent import BaseAgent, BaseAgentState
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event, EventActions
from google.adk.utils.context_utils import Aclosing
from google.adk.utils.feature_decorator import experimental

from .common_agents.ad_content_generator.tools import save_final_report_tool
from .shared_libraries.config import config
from .shared_libraries.utils import upload_blob_to_gcs, download_blob
from .shared_libraries.fidelity_eval.gecko import evaluate as gecko_evaluate

logger = logging.getLogger("google_adk." + __name__)

# Cached media gen client (us-central1 for Imagen/Veo, NOT "global")
_media_client = None

def _get_media_client():
    """Get or create a cached genai.Client for media gen APIs (Imagen, Veo).

    Media gen APIs (Imagen 4, Veo 3.1) require us-central1, NOT "global"
    which is set as GOOGLE_CLOUD_LOCATION for Gemini 3 models.
    """
    global _media_client
    if _media_client is None:
        _media_client = genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "wortz-project-352116"),
            location="us-central1",
        )
        logger.info(
            f"[MediaClient] Created cached client: project={_media_client._api_client.project}, location={_media_client._api_client.location}"
        )
    return _media_client


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

STAGES = ["TRENDS", "RESEARCH", "AD_CREATIVE", "IMAGE_GEN", "AV_STUDIO", "FOCUS_GROUP", "SAVE_REPORT", "COMPLETE"]

MAX_CREATIVE_ATTEMPTS = 15  # Max times to re-enter IMAGE_GEN before skipping
AV_STUDIO_MAX_RUNS = 5  # Max AV_STUDIO invocations before skipping
AE_WAVE_POLL_BUDGET = 55  # seconds to poll Veo within a single AE wave

def _dynamic_stage_message(stage: str, state: dict) -> str:
    """Build contextual, CEO-friendly status messages using campaign metadata."""
    brand = state.get("brand", "")
    product = state.get("target_product", "")
    audience = state.get("target_audience", "")
    selling_points = state.get("key_selling_points", "")

    # Avoid "Tide Tide Fabric Softener" — if product already contains brand, use product alone
    if brand and product and product.lower().startswith(brand.lower()):
        descriptor = product
    elif brand and product:
        descriptor = f"{brand} {product}"
    else:
        descriptor = product or brand or "the campaign"
    # Extract first selling point for flavor text
    first_sp = selling_points.split(".")[0].strip() if selling_points else ""

    messages = {
        "TRENDS": (
            f"Scanning real-time Google Trends and YouTube for {descriptor} — "
            f"finding the cultural moments that will make this campaign resonate."
        ),
        "RESEARCH": (
            f"Deep-diving into market intelligence for {descriptor}"
            + (f" — analyzing what motivates {audience}" if audience else "")
            + ". Synthesizing YouTube, Google Search, and competitive insights."
        ),
        "AD_CREATIVE": (
            f"Brainstorming ad concepts for {descriptor}"
            + (f" — leading with '{first_sp}'" if first_sp else "")
            + ". Drafting headlines, copy, and visual concepts."
        ),
        "IMAGE_GEN": (
            f"Rendering reference images for {descriptor} — product hero, lifestyle, and trend aesthetic."
        ),
        "AV_STUDIO": (
            f"Directing a video commercial for {descriptor} — cinematic footage with Veo."
        ),
        "FOCUS_GROUP": (
            f"Assembling a simulated focus group to evaluate the {descriptor} campaign"
            + (f" — panelists drawn from {audience}" if audience else "")
            + ". Scoring creative impact, brand alignment, and audience appeal."
        ),
        "SAVE_REPORT": (
            f"Compiling the final campaign brief for {descriptor} — "
            f"research findings, creative assets, and focus group scores packaged into a PDF."
        ),
        "COMPLETE": (
            f"Campaign pipeline complete for {descriptor}! "
            f"All assets — research report, ad creatives, commercial, and focus group evaluation — are ready for review."
        ),
    }
    return messages.get(stage, f"Running stage: {stage}")

STAGE_AGENT_MAP = {
    "RESEARCH": "research_agent",
    "AD_CREATIVE": "ad_creative_agent",
    "FOCUS_GROUP": "focus_group_evaluator_agent",
    # TRENDS, IMAGE_GEN, AV_STUDIO, SAVE_REPORT are deterministic — no agent needed
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
        state = ctx.session.state

        # Auto-detect autopilot from user message (e.g. GE sends raw message text)
        if not state.get("autopilot_mode") and not state.get("_state_init"):
            user_text = ""
            if ctx.user_content and ctx.user_content.parts:
                for part in ctx.user_content.parts:
                    if hasattr(part, "text") and part.text:
                        user_text += part.text.lower()
            if "autopilot" in user_text:
                init_event = self._status_event(ctx, "Autopilot mode activated — running full pipeline automatically.")
                init_event.actions.state_delta["autopilot_mode"] = True
                init_event.actions.state_delta["_state_init"] = True
                # Extract campaign parameters from message if present
                import re
                brand_match = re.search(r'brand:\s*(\w+)', user_text, re.IGNORECASE)
                product_match = re.search(r'product:\s*(.+?)(?:\n|$)', user_text, re.IGNORECASE)
                audience_match = re.search(r'(?:target audience|audience):\s*(.+?)(?:\n|$)', user_text, re.IGNORECASE)
                ksp_match = re.search(r'(?:key selling points|selling points|features):\s*(.+?)(?:\n|$)', user_text, re.IGNORECASE)
                if brand_match:
                    init_event.actions.state_delta["brand"] = brand_match.group(1).strip()
                if product_match:
                    init_event.actions.state_delta["target_product"] = product_match.group(1).strip()
                if audience_match:
                    init_event.actions.state_delta["target_audience"] = audience_match.group(1).strip()
                if ksp_match:
                    init_event.actions.state_delta["key_selling_points"] = ksp_match.group(1).strip()
                init_event.actions.state_delta["commercial_duration"] = 8
                yield init_event
                # Refresh state after delta
                state = ctx.session.state

        # Reconstruct state from conversation history (GE may not persist state_delta between waves)
        async for event in self._reconstruct_state_from_history(ctx):
            yield event
        state = ctx.session.state

        stage = self._determine_stage(ctx)
        state = ctx.session.state

        # Track image gen attempts to break infinite loops
        if stage == "IMAGE_GEN":
            creative_attempts = state.get("_creative_pipeline_attempts", 0) + 1
            if creative_attempts > MAX_CREATIVE_ATTEMPTS:
                logger.warning(
                    f"[CampaignOrchestrator] Image gen pipeline exhausted "
                    f"({creative_attempts} attempts). Skipping to FOCUS_GROUP."
                )
                stage = "FOCUS_GROUP"
            else:
                # Persist counter via state_delta event
                counter_event = self._status_event(
                    ctx, f"Image generation attempt {creative_attempts}/{MAX_CREATIVE_ATTEMPTS}..."
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
        status_msg = _dynamic_stage_message(stage, dict(state))
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part(text=status_msg)],
            ),
        )

        # --- Handle each stage ---

        if stage == "TRENDS" and state.get("autopilot_mode"):
            async for event in self._gather_trends_deterministic(ctx):
                yield event
        elif stage == "TRENDS":
            async for event in self._gather_trends_interactive(ctx):
                yield event
        elif stage == "RESEARCH":
            async for event in self._run_agent_and_capture(ctx, "research_agent", "combined_final_cited_report"):
                yield event
            # Mark research complete
            done_event = self._status_event(ctx, "Research pipeline complete.")
            done_event.actions.state_delta["_research_pipeline_complete"] = True
            yield done_event
        elif stage == "AD_CREATIVE":
            async for event in self._run_agent_and_capture(ctx, "ad_creative_agent", "ad_creative_output"):
                yield event
            done_event = self._status_event(ctx, "Ad creative pipeline complete.")
            done_event.actions.state_delta["_ad_creative_complete"] = True
            yield done_event
        elif stage == "IMAGE_GEN":
            async for event in self._generate_images_deterministic(ctx):
                yield event
        elif stage == "AV_STUDIO":
            # Track AV studio runs
            av_runs = state.get("_av_studio_runs", 0) + 1
            av_event = self._status_event(ctx, f"AV Studio run {av_runs}/{AV_STUDIO_MAX_RUNS}...")
            av_event.actions.state_delta["_av_studio_runs"] = av_runs
            yield av_event
            async for event in self._generate_commercial_deterministic(ctx):
                yield event
        elif stage == "FOCUS_GROUP":
            # Track focus group attempts to prevent infinite loop
            fg_count = state.get("_focus_group_attempts", 0) + 1
            fg_event = Event(
                invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                actions=EventActions(state_delta={"_focus_group_attempts": fg_count}),
            )
            yield fg_event
            # Run focus group agent and capture evaluation text
            _fg_persisted = False
            _captured_fg_parts: list[str] = []
            target = self._get_agent_for_stage_by_name("focus_group_evaluator_agent")
            if target:
                async with Aclosing(target.run_async(ctx)) as agen:
                    async for event in agen:
                        yield event
                        # Capture focus group text and persist via state_delta
                        if not _fg_persisted:
                            if getattr(event, "content", None):
                                for part in (event.content.parts or []):
                                    if getattr(part, "text", None):
                                        _captured_fg_parts.append(part.text)
                            fg_text = "\n".join(_captured_fg_parts)
                            if len(fg_text) > 200:
                                persist_event = Event(
                                    invocation_id=ctx.invocation_id,
                                    author=self.name,
                                    branch=ctx.branch,
                                    actions=EventActions(
                                        state_delta={
                                            "focus_group_evaluation": fg_text,
                                            "_focus_group_complete": True,
                                        },
                                    ),
                                )
                                yield persist_event
                                _fg_persisted = True
                        if ctx.should_pause_invocation(event):
                            descriptor = f"{state.get('brand', '')} {state.get('target_product', '')}".strip() or "the campaign"
                            wave_msg = f"{status_msg.rstrip('.')} — say 'continue' to proceed."
                            yield self._status_event(ctx, wave_msg)
                            return
        elif stage == "SAVE_REPORT":
            async for event in self._save_final_report(ctx):
                yield event

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
        trends_waves = state.get("_trends_wave_count", 0)
        logger.info(
            f"[CampaignOrchestrator] _determine_stage: "
            f"search_trends={search_trends}, has={self._has_trends(search_trends)}, "
            f"yt_trends={yt_trends}, has={self._has_trends(yt_trends)}, "
            f"trends_waves={trends_waves}"
        )
        if not self._has_trends(search_trends) or not self._has_trends(yt_trends):
            return "TRENDS"

        # Stage 1: Need research report
        report = state.get("combined_final_cited_report", "")
        research_done = state.get("_research_pipeline_complete", False)
        if not research_done and (not report or len(str(report)) < 500):
            return "RESEARCH"

        # Stage 2: Need ad copies and visual concepts
        ad_copies = state.get("final_select_ad_copies", {})
        if isinstance(ad_copies, dict):
            ad_copies = ad_copies.get("final_select_ad_copies", [])
        if not ad_copies and not state.get("_ad_creative_complete"):
            return "AD_CREATIVE"

        # Stage 3: Need 3 reference images
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(img_keys, dict):
            img_keys = img_keys.get("img_artifact_keys", [])
        if not img_keys or len(img_keys) < 3:
            img_attempts = state.get("_creative_pipeline_attempts", 0)
            if img_attempts < MAX_CREATIVE_ATTEMPTS:
                return "IMAGE_GEN"

        # Stage 4: Need commercial video
        has_commercial = bool(state.get("commercial_artifact"))
        clips_cache = state.get("_commercial_clips", {})
        has_pending_veo = bool(clips_cache.get("_pending_veo_op")) if isinstance(clips_cache, dict) else False
        av_runs = state.get("_av_studio_runs", 0)
        if not has_commercial and (has_pending_veo or av_runs < AV_STUDIO_MAX_RUNS):
            return "AV_STUDIO"

        # Stage 5: Need focus group evaluation
        fg_attempts = state.get("_focus_group_attempts", 0)
        if not state.get("focus_group_evaluation") and not state.get("_focus_group_complete") and fg_attempts < 5:
            return "FOCUS_GROUP"

        # Stage 6: Need final report PDF
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

    def _get_agent_for_stage_by_name(self, name: str):
        """Look up a sub-agent by name."""
        for agent in self.sub_agents:
            if agent.name == name:
                return agent
        return None

    async def _run_agent_and_capture(
        self, ctx: InvocationContext, agent_name: str, state_key: str
    ) -> AsyncGenerator[Event, None]:
        """Run a sub-agent and capture its text output via state_delta.

        This replaces output_key — the orchestrator captures the longest non-thought
        text from the agent's events and persists it via its own state_delta event
        AND directly to ctx.session.state for same-invocation reads.
        """
        target = self._get_agent_for_stage_by_name(agent_name)
        if not target:
            yield self._status_event(ctx, f"Agent '{agent_name}' not found in sub_agents")
            return

        captured_text = ""
        all_text_parts: list[str] = []
        async with Aclosing(target.run_async(ctx)) as agen:
            async for event in agen:
                yield event
                # Capture non-thought text from model events — keep the LONGEST
                if hasattr(event, 'content') and event.content:
                    for part in (event.content.parts or []):
                        if hasattr(part, 'text') and part.text and len(part.text) > 100:
                            if not getattr(part, 'thought', False):
                                all_text_parts.append(part.text)
                                if len(part.text) > len(captured_text):
                                    captured_text = part.text
                if ctx.should_pause_invocation(event):
                    # Persist what we have before pausing
                    if captured_text and len(captured_text) > 200:
                        ctx.session.state[state_key] = captured_text
                        persist_event = self._status_event(ctx, f"Persisting {state_key} ({len(captured_text)} chars) before wave pause")
                        persist_event.actions.state_delta[state_key] = captured_text
                        yield persist_event
                    return

        # Persist captured text — both via state_delta AND direct state write
        if captured_text and len(captured_text) > 200:
            ctx.session.state[state_key] = captured_text
            persist_event = self._status_event(ctx, f"{state_key} captured ({len(captured_text)} chars)")
            persist_event.actions.state_delta[state_key] = captured_text
            yield persist_event
            logger.info(f"[CampaignOrchestrator] Captured {state_key}: {len(captured_text)} chars (from {len(all_text_parts)} text parts)")
        else:
            # Fallback: concatenate all text parts if individual parts were too short
            combined = "\n\n".join(all_text_parts)
            if combined and len(combined) > 200:
                ctx.session.state[state_key] = combined
                persist_event = self._status_event(ctx, f"{state_key} captured ({len(combined)} chars, concatenated from {len(all_text_parts)} parts)")
                persist_event.actions.state_delta[state_key] = combined
                yield persist_event
                logger.info(f"[CampaignOrchestrator] Captured {state_key} via concatenation: {len(combined)} chars")
            else:
                logger.warning(f"[CampaignOrchestrator] Failed to capture {state_key} — no qualifying text found (parts: {len(all_text_parts)}, longest: {len(captured_text)})")

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

    async def _reconstruct_state_from_history(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Scan conversation history to reconstruct ALL state that may not have persisted.

        On GE, state_delta may not persist between waves, but conversation history does.
        This method scans ALL past events for state_delta values and re-persists any
        that are missing from current session state. This covers trends, research,
        creative, focus group, and all other pipeline state.
        """
        import re
        state = ctx.session.state

        # Keys we care about reconstructing (pipeline-critical state)
        RECONSTRUCTABLE_KEYS = {
            # Campaign metadata
            "brand", "target_product", "target_audience", "key_selling_points",
            "commercial_duration", "autopilot_mode",
            # Trends
            "target_search_trends", "target_yt_trends", "trend_relevance_rationale",
            # Research pipeline
            "gs_web_search_insights", "yt_web_search_insights", "campaign_web_search_insights",
            "combined_web_search_insights", "combined_research_evaluation",
            "combined_final_cited_report", "prior_campaign_insights",
            "_memory_recall_done", "_research_pipeline_complete", "_research_parallel_waves",
            "yt_video_analysis", "sources",
            # Creative pipeline
            "ad_copy_draft", "ad_copy_critique", "ad_copy_final",
            "ad_creative_output", "_ad_creative_complete",
            "img_artifact_keys", "vid_artifact_keys", "commercial_artifact",
            "_creative_pipeline_attempts", "_av_studio_runs", "_commercial_clips",
            "reference_images",
            # Focus group
            "focus_group_evaluation", "focus_group_panelists",
            "_focus_group_attempts", "_focus_group_complete",
            # Final report
            "final_report_with_citations",
            # GCS
            "gcs_folder",
        }

        reconstructed = {}

        # Pass 1: Scan ALL events for state_delta values
        for event in (ctx.session.events or []):
            if hasattr(event, "actions") and event.actions and event.actions.state_delta:
                delta = event.actions.state_delta
                for key in RECONSTRUCTABLE_KEYS:
                    if key in delta and delta[key]:
                        # Always take the LATEST value (later events override earlier)
                        reconstructed[key] = delta[key]

            # Also check function_response parts for save tool results
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        fn_name = part.function_response.name if hasattr(part.function_response, "name") else ""
                        fn_result = part.function_response.response if hasattr(part.function_response, "response") else {}
                        if fn_name == "save_search_trends_to_session_state" and fn_result.get("status") == "ok":
                            saved_data = fn_result.get("saved_data", {})
                            if saved_data:
                                reconstructed["target_search_trends"] = {"target_search_trends": [saved_data]}
                        elif fn_name == "save_yt_trends_to_session_state" and fn_result.get("status") == "ok":
                            saved_data = fn_result.get("saved_data", {})
                            if saved_data:
                                reconstructed["target_yt_trends"] = {"target_yt_trends": [saved_data]}

                    # Check memorize calls for brand data
                    if hasattr(part, "function_call") and part.function_call:
                        fn_name = getattr(part.function_call, "name", "")
                        fn_args = getattr(part.function_call, "args", {}) or {}
                        if fn_name == "memorize":
                            key = fn_args.get("key", "")
                            val = fn_args.get("value", "")
                            if key in RECONSTRUCTABLE_KEYS and val:
                                reconstructed[key] = val

            # Scan user messages for brand info (fallback if tools weren't called)
            if hasattr(event, "content") and event.content:
                if getattr(event.content, "role", "") == "user":
                    for part in (event.content.parts or []):
                        if hasattr(part, "text") and part.text and "brand" not in reconstructed:
                            text = part.text
                            brand_m = re.search(r'brand:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
                            if brand_m:
                                reconstructed["brand"] = brand_m.group(1).strip()
                                prod_m = re.search(r'product:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
                                aud_m = re.search(r'(?:audience):\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
                                feat_m = re.search(r'(?:features|selling points):\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
                                if prod_m:
                                    reconstructed["target_product"] = prod_m.group(1).strip()
                                if aud_m:
                                    reconstructed["target_audience"] = aud_m.group(1).strip()
                                if feat_m:
                                    reconstructed["key_selling_points"] = feat_m.group(1).strip()

        # Pass 2: Only emit state that's actually missing from current session state
        missing = {}
        for key, val in reconstructed.items():
            current = state.get(key)
            if not current:
                missing[key] = val
            elif key == "combined_web_search_insights" and len(str(val)) > len(str(current)):
                # Take the longer (more complete) version
                missing[key] = val
            elif key == "combined_final_cited_report" and len(str(val)) > len(str(current)):
                missing[key] = val

        # Emit reconstructed state AND apply directly to session state
        # (state_delta events may not be applied to ctx.session.state within same invocation)
        if missing:
            logger.info(
                f"[CampaignOrchestrator] Reconstructed {len(missing)} state keys from history: "
                f"{list(missing.keys())}"
            )
            # Apply directly so downstream code in this invocation sees the values
            for key, val in missing.items():
                ctx.session.state[key] = val
            # Also emit as state_delta for AE persistence
            reconstruct_event = Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                actions=EventActions(state_delta=missing),
            )
            yield reconstruct_event
        else:
            logger.info("[CampaignOrchestrator] No state reconstruction needed — all keys present")

    async def _persist_trends_from_conversation(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """After LLM trends agent runs, scan latest events for tool call results and persist."""
        # The _reconstruct_state_from_history at the start of the next wave handles this
        # This method is a no-op — the real work happens at wave entry
        return
        yield  # Make it a generator

    async def _gather_trends_interactive(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Deterministic interactive trend selection — no LLM needed.

        Stateless per-wave: re-parses brand from user text and re-fetches trends
        each wave to avoid state persistence issues on AE/GE. The only state
        that must persist between waves is target_search_trends (saved via state_delta
        when the user picks a search trend).

        Flow:
          Wave 1: No brand in message -> ask for campaign metadata
          Wave 2: Brand in message, no search trend -> parse brand, fetch & display Google trends
          Wave 3: Number in message, no search trend saved -> re-fetch trends, save pick, show YT trends
          Wave 4: Number in message, has search trend -> save YT pick, advance to RESEARCH
        """
        import re
        from .common_agents.trend_assistant.tools import get_daily_gtrends, get_youtube_trends

        state = ctx.session.state

        # --- Extract user message text ---
        user_text = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if hasattr(part, "text") and part.text:
                    user_text += part.text
        user_text_stripped = user_text.strip()

        # --- Always try to parse and persist brand from user text ---
        has_brand = bool(state.get("brand"))
        if not has_brand:
            brand_match = re.search(r'brand:\s*(.+?)(?:\n|$)', user_text, re.IGNORECASE)
            product_match = re.search(r'product:\s*(.+?)(?:\n|$)', user_text, re.IGNORECASE)
            audience_match = re.search(r'(?:target audience|audience):\s*(.+?)(?:\n|$)', user_text, re.IGNORECASE)
            ksp_match = re.search(r'(?:key selling points|selling points|features):\s*(.+?)(?:\n|$)', user_text, re.IGNORECASE)

            if brand_match:
                meta_delta = {
                    "brand": brand_match.group(1).strip(),
                    "commercial_duration": 8,
                }
                if product_match:
                    meta_delta["target_product"] = product_match.group(1).strip()
                if audience_match:
                    meta_delta["target_audience"] = audience_match.group(1).strip()
                if ksp_match:
                    meta_delta["key_selling_points"] = ksp_match.group(1).strip()

                # Persist brand via state_delta event (separate from content)
                brand_event = Event(
                    invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta=meta_delta),
                )
                yield brand_event
                has_brand = True

                # Fetch Google trends and display them in the SAME wave
                try:
                    gtrends_result = get_daily_gtrends()
                    all_trends = _parse_search_trends(gtrends_result)
                except Exception as e:
                    logger.warning(f"[CampaignOrchestrator] Failed to fetch search trends: {e}")
                    all_trends = []

                if all_trends:
                    rows = []
                    for i, t in enumerate(all_trends):
                        rows.append(f"| {i+1} | {t['trend_title']} | {t['trend_rank']} | {t['trend_refresh_date']} |")
                    table = (
                        "| # | Trend | Rank | Date |\n"
                        "|---|-------|------|------|\n"
                        + "\n".join(rows)
                    )
                    yield Event(
                        invocation_id=ctx.invocation_id,
                        author=self.name,
                        branch=ctx.branch,
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text=(
                                f"Campaign details saved: **{meta_delta.get('brand', '')}** — "
                                f"{meta_delta.get('target_product', '')} for {meta_delta.get('target_audience', '')}\n\n"
                                f"**Top {len(all_trends)} Google Search Trends** (live data)\n\n"
                                f"{table}\n\n"
                                f"Which trend would you like to target? Enter a number (1-{len(all_trends)})."
                            ))],
                        ),
                    )
                else:
                    yield self._status_event(ctx, "Could not fetch Google trends — auto-selecting...")
                    async for event in self._gather_trends_deterministic(ctx):
                        yield event
                return
            else:
                # No brand info — ask for it
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    branch=ctx.branch,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=(
                            "Welcome! Let's build your marketing campaign brief.\n\n"
                            "Please provide your campaign details:\n\n"
                            "```\n"
                            "Brand: [brand name]\n"
                            "Product: [product name]\n"
                            "Audience: [target audience]\n"
                            "Features: [key selling points]\n"
                            "```\n\n"
                            "For example:\n"
                            "```\n"
                            "Brand: Tide\n"
                            "Product: Tide Fabric Softener\n"
                            "Audience: Gen Z\n"
                            "Features: New Hibiscus Scent\n"
                            "```"
                        ))],
                    ),
                )
                return

        # --- Sub-state: need Google Search trend pick? ---
        has_search = self._has_trends(state.get("target_search_trends"))
        if not has_search:
            # User should be sending a number to pick a search trend
            pick_num = self._parse_user_pick(user_text_stripped, 25)

            # Re-fetch trends (stateless — no cache dependency)
            try:
                gtrends_result = get_daily_gtrends()
                all_trends = _parse_search_trends(gtrends_result)
            except Exception as e:
                logger.warning(f"[CampaignOrchestrator] Failed to re-fetch search trends: {e}")
                all_trends = []

            if pick_num is not None and all_trends and pick_num < len(all_trends):
                selected = all_trends[pick_num]
                search_delta = {"target_search_trends": [selected]}

                # Persist search trend via state_delta
                search_event = Event(
                    invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta={"target_search_trends": search_delta}),
                )
                yield search_event

                # Fetch YouTube trends and display in SAME wave
                try:
                    yt_result = get_youtube_trends()
                except Exception as e:
                    logger.warning(f"[CampaignOrchestrator] Failed to fetch YouTube trends: {e}")
                    yt_result = {}

                if yt_result:
                    yt_list = []
                    for key in sorted(yt_result.keys()):
                        vid = yt_result[key]
                        yt_list.append({
                            "video_title": vid.get("videoTitle", ""),
                            "video_duration": vid.get("duration", ""),
                            "video_url": vid.get("videoURL", ""),
                        })

                    lines = []
                    for i, vid in enumerate(yt_list):
                        lines.append(f"| {i+1} | {vid['video_title']} | {vid['video_duration']} | [Watch]({vid['video_url']}) |")
                    table = (
                        "| # | Title | Duration | Link |\n"
                        "|---|-------|----------|------|\n"
                        + "\n".join(lines)
                    )

                    yield Event(
                        invocation_id=ctx.invocation_id,
                        author=self.name,
                        branch=ctx.branch,
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text=(
                                f"Search trend selected: **\"{selected['trend_title']}\"** (rank #{selected['trend_rank']})\n\n"
                                f"**Top {len(yt_list)} Trending YouTube Videos** (live data)\n\n"
                                f"{table}\n\n"
                                f"Which video would you like to target? Enter a number (1-{len(yt_list)})."
                            ))],
                        ),
                    )
                else:
                    yield self._status_event(ctx, "Could not fetch YouTube trends — auto-selecting...")
                    async for event in self._gather_trends_deterministic(ctx):
                        yield event
                return
            else:
                # Show trends again (user sent non-numeric or invalid)
                if all_trends:
                    rows = []
                    for i, t in enumerate(all_trends):
                        rows.append(f"| {i+1} | {t['trend_title']} | {t['trend_rank']} | {t['trend_refresh_date']} |")
                    table = (
                        "| # | Trend | Rank | Date |\n"
                        "|---|-------|------|------|\n"
                        + "\n".join(rows)
                    )
                    yield Event(
                        invocation_id=ctx.invocation_id,
                        author=self.name,
                        branch=ctx.branch,
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text=(
                                f"**Google Search Trends** — please enter a number (1-{len(all_trends)}) to select a trend:\n\n"
                                f"{table}"
                            ))],
                        ),
                    )
                else:
                    yield self._status_event(ctx, "Could not fetch trends — auto-selecting...")
                    async for event in self._gather_trends_deterministic(ctx):
                        yield event
                return

        # --- Sub-state: need YouTube trend pick? ---
        has_yt = self._has_trends(state.get("target_yt_trends"))
        if not has_yt:
            pick_num = self._parse_user_pick(user_text_stripped, 10)

            # Re-fetch YouTube trends (stateless)
            try:
                yt_result = get_youtube_trends()
            except Exception as e:
                logger.warning(f"[CampaignOrchestrator] Failed to re-fetch YouTube trends: {e}")
                yt_result = {}

            yt_list = []
            if yt_result:
                for key in sorted(yt_result.keys()):
                    vid = yt_result[key]
                    yt_list.append({
                        "video_title": vid.get("videoTitle", ""),
                        "video_duration": vid.get("duration", ""),
                        "video_url": vid.get("videoURL", ""),
                    })

            if pick_num is not None and yt_list and pick_num < len(yt_list):
                selected = yt_list[pick_num]
                yt_delta = {"target_yt_trends": [selected]}

                # Build campaign summary
                brand = state.get("brand", "")
                product = state.get("target_product", "")
                audience = state.get("target_audience", "")
                features = state.get("key_selling_points", "")
                search_trend_name = ""
                st = state.get("target_search_trends")
                if isinstance(st, dict):
                    st_list = st.get("target_search_trends", [])
                    if st_list:
                        search_trend_name = st_list[0].get("trend_title", "")
                elif isinstance(st, list) and st:
                    search_trend_name = st[0].get("trend_title", "")

                # Persist YT trend via state_delta
                yt_event = Event(
                    invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta={"target_yt_trends": yt_delta}),
                )
                yield yt_event

                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    branch=ctx.branch,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=(
                            f"YouTube trend selected: **\"{selected.get('video_title', '')}\"**\n\n"
                            f"---\n\n"
                            f"**Campaign Brief Complete!**\n\n"
                            f"| Field | Value |\n"
                            f"|-------|-------|\n"
                            f"| Brand | {brand} |\n"
                            f"| Product | {product} |\n"
                            f"| Audience | {audience} |\n"
                            f"| Features | {features} |\n"
                            f"| Search Trend | {search_trend_name} |\n"
                            f"| YouTube Trend | {selected.get('video_title', '')} |\n\n"
                            f"Launching research pipeline — deep-diving into market intelligence..."
                        ))],
                    ),
                )
                return
            else:
                # Show YT trends again
                if yt_list:
                    lines = []
                    for i, vid in enumerate(yt_list):
                        lines.append(f"| {i+1} | {vid['video_title']} | {vid['video_duration']} | [Watch]({vid['video_url']}) |")
                    table = (
                        "| # | Title | Duration | Link |\n"
                        "|---|-------|----------|------|\n"
                        + "\n".join(lines)
                    )
                    yield Event(
                        invocation_id=ctx.invocation_id,
                        author=self.name,
                        branch=ctx.branch,
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text=(
                                f"**YouTube Trends** — please enter a number (1-{len(yt_list)}) to select a video:\n\n"
                                f"{table}"
                            ))],
                        ),
                    )
                else:
                    yield self._status_event(ctx, "Could not fetch YouTube trends — auto-selecting...")
                    async for event in self._gather_trends_deterministic(ctx):
                        yield event
                return

        # Both trends selected — advance
        yield self._status_event(ctx, "All trends captured. Proceeding to research...")

    def _parse_user_pick(self, user_text: str, max_items: int) -> int | None:
        """Parse a numeric pick from user text. Returns 0-indexed or None."""
        import re
        numbers = re.findall(r'\b(\d+)\b', user_text.strip())
        if numbers:
            pick = int(numbers[0])
            if 1 <= pick <= max_items:
                return pick - 1
        return None

    # -------------------------------------------------------------------------
    # IMAGE_GEN — deterministic Imagen 4 image generation
    # -------------------------------------------------------------------------

    async def _generate_images_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate 3 purpose-built ASSET reference images for Veo video generation.

        1. Product ASSET — hero product shot
        2. Person ASSET — model/person for the ad
        3. Trend ASSET — trend-driven scene blending product + cultural moment

        All images are ASSET type (Veo only supports one reference type per call).
        All images scored with Gecko fidelity. One image per AE wave.
        """
        state = ctx.session.state
        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "consumers")
        brand = state.get("brand", "")
        ksp = state.get("key_selling_points", "")
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")
        MAX_IMAGES = 3  # Product ASSET + Person ASSET + Trend ASSET

        existing_imgs = state.get("img_artifact_keys", {})
        if isinstance(existing_imgs, dict):
            existing_imgs = existing_imgs.get("img_artifact_keys", [])
        if not isinstance(existing_imgs, list):
            existing_imgs = []
        already_generated = len(existing_imgs)

        if already_generated >= MAX_IMAGES:
            yield self._status_event(ctx, f"All {MAX_IMAGES} reference images already generated.")
            return

        # Get the best ad idea name for naming
        ad_copies = state.get("final_select_ad_copies", {})
        if isinstance(ad_copies, dict):
            ad_copies = ad_copies.get("final_select_ad_copies", [])
        idea_name = "campaign"
        if ad_copies and isinstance(ad_copies[0], dict):
            idea_name = ad_copies[0].get("name", ad_copies[0].get("concept_name", "campaign"))
        idea_name = idea_name.replace(",", "").replace(" ", "_")

        # Get trend titles for trend ASSET image
        trend_desc = state.get("target_search_trends", {})
        search_trend_title = ""
        if isinstance(trend_desc, dict):
            trends_list = trend_desc.get("target_search_trends", [])
            if trends_list:
                search_trend_title = trends_list[0].get("title", "") if isinstance(trends_list[0], dict) else str(trends_list[0])

        yt_trend_desc = state.get("target_yt_trends", {})
        yt_trend_title = ""
        if isinstance(yt_trend_desc, dict):
            yt_list = yt_trend_desc.get("target_yt_trends", [])
            if yt_list:
                yt_trend_title = yt_list[0].get("title", "") if isinstance(yt_list[0], dict) else str(yt_list[0])

        # Get the winning ad copy's headline/concept for creative direction
        ad_headline = ""
        ad_rationale = ""
        if ad_copies and isinstance(ad_copies[0], dict):
            ad_headline = ad_copies[0].get("headline", "")
            ad_rationale = ad_copies[0].get("rationale", "")

        # Get visual concept prompt if available
        visual_concepts = state.get("final_select_visual_concepts", {})
        if isinstance(visual_concepts, dict):
            visual_concepts = visual_concepts.get("final_select_visual_concepts", [])
        visual_prompt_hint = ""
        if visual_concepts and isinstance(visual_concepts[0], dict):
            visual_prompt_hint = visual_concepts[0].get("prompt", "")

        # Build trend context string
        trend_context = ""
        if search_trend_title:
            trend_context += f'inspired by the "{search_trend_title}" trend'
        if yt_trend_title:
            trend_context += f' and the "{yt_trend_title}" YouTube trend' if trend_context else f'inspired by the "{yt_trend_title}" YouTube trend'

        # Build 3 purpose-built reference images with dynamic brand/trend context
        shot_list = [
            # Shot 1: Product ASSET — hero product shot with brand identity
            {
                "concept_name": f"{idea_name}_product_asset",
                "shot_type": "product_asset",
                "reference_type": "ASSET",
                "prompt": (
                    f"Studio product photo: {brand} {product} bottle prominently displayed"
                    + (f", {ksp}" if ksp else "")
                    + ". Clean white background, dramatic studio lighting, premium beauty product aesthetic. "
                    f"No text, no watermarks, no logos."
                ),
            },
            # Shot 2: Person ASSET — model/person reflecting target audience + ad concept
            {
                "concept_name": f"{idea_name}_person_asset",
                "shot_type": "person_asset",
                "reference_type": "ASSET",
                "prompt": (
                    f"Lifestyle photo: {audience} person"
                    + (f" embodying \"{ad_headline}\"" if ad_headline else "")
                    + f", interacting with {product}"
                    + (f", {trend_context}" if trend_context else "")
                    + ". Warm natural light, modern setting, authentic emotion. "
                    f"No text, no watermarks."
                ),
            },
            # Shot 3: Trend ASSET — scene blending product with the cultural trend moment
            {
                "concept_name": f"{idea_name}_trend_asset",
                "shot_type": "trend_asset",
                "reference_type": "ASSET",
                "prompt": (
                    f"Cinematic lifestyle scene: {brand} {product}"
                    + (f" placed in a setting that evokes {trend_context}" if trend_context else "")
                    + (f". Visual direction: {visual_prompt_hint[:250]}" if visual_prompt_hint else "")
                    + f". The product is clearly visible in the scene"
                    + f", {audience} aesthetic, aspirational and culturally resonant"
                    + ". Cinematic color grading, golden-hour lighting. "
                    f"No text, no watermarks, no logos."
                ),
            },
        ]

        # Generate one image per wave (AE-safe)
        img_idx = already_generated
        if img_idx >= len(shot_list):
            yield self._status_event(ctx, f"All {len(shot_list)} images already generated.")
            return

        # Track failures per image index to avoid infinite retry
        img_fail_key = f"_img_fail_{img_idx}"
        img_failures = state.get(img_fail_key, 0)
        MAX_IMG_RETRIES = 5

        shot = shot_list[img_idx]
        concept_name = shot["concept_name"]
        prompt = shot["prompt"]

        if img_failures >= MAX_IMG_RETRIES:
            # Skip this image after too many failures — add placeholder to advance
            import re as _re
            logger.warning(f"[ImageGen] Skipping image {img_idx+1} after {img_failures} failures")
            _skip_safe = _re.sub(r"[^a-zA-Z0-9_\-]", "", concept_name.replace(" ", "_"))
            placeholder = {
                "artifact_key": f"skipped_{_skip_safe}_0.png",
                "concept_name": concept_name,
                "shot_type": shot["shot_type"],
                "reference_type": shot.get("reference_type", "ASSET"),
                "skipped": True,
            }
            new_list = list(existing_imgs) + [placeholder]
            skip_event = self._status_event(
                ctx, f"Image {img_idx + 1}/{MAX_IMAGES} skipped after {img_failures} attempts — advancing pipeline."
            )
            skip_event.actions.state_delta["img_artifact_keys"] = {"img_artifact_keys": new_list}
            yield skip_event
            return

        # Pre-increment failure counter BEFORE calling generate_images().
        # If AE wave times out during the call, the counter is already saved,
        # preventing infinite retry on the same image.
        pre_fail_event = self._status_event(ctx, f"Generating image {img_idx + 1}/{MAX_IMAGES} ({shot['shot_type']}: {concept_name})...")
        pre_fail_event.actions.state_delta[img_fail_key] = img_failures + 1
        yield pre_fail_event

        try:
            import re as _re
            from google.genai.types import GenerateImagesConfig
            img_client = _get_media_client()
            # Sanitize name: alphanumeric, underscores, hyphens only
            safe_name = _re.sub(r"[^a-zA-Z0-9_\-]", "", concept_name.replace(" ", "_"))
            artifact_key = f"{safe_name}_0.png"
            gcs_uri = ""

            # Generate image (no output_gcs_uri — upload separately for reliability)
            img_config = GenerateImagesConfig(number_of_images=1)
            _img_start_t = time.time()
            response = img_client.models.generate_images(
                model="imagen-4.0-generate-preview-06-06",
                prompt=prompt,
                config=img_config,
            )

            if response and response.generated_images:
                gen_img = response.generated_images[0]
                image_bytes = gen_img.image.image_bytes if gen_img.image else None

                if bucket and gcs_folder and image_bytes:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(image_bytes)
                        tmp_path = tmp.name
                    try:
                        upload_blob_to_gcs(
                            source_file_name=tmp_path,
                            destination_blob_name=os.path.join(gcs_folder, artifact_key),
                        )
                        gcs_uri = f"{bucket}/{gcs_folder}/{artifact_key}"
                    finally:
                        os.unlink(tmp_path)

                img_meta = {
                    "artifact_key": artifact_key,
                    "img_prompt": prompt[:500],
                    "concept": concept_name,
                    "concept_name": concept_name,
                    "headline": shot.get("headline", ""),
                    "caption": shot.get("caption", ""),
                    "shot_type": shot["shot_type"],
                    "reference_type": shot.get("reference_type", "ASSET"),
                    "auto_saved": True,
                }
                if gcs_uri:
                    img_meta["gcs_uri"] = gcs_uri

                # Gecko fidelity (best-effort, skip if tight on time)
                fidelity_score = None
                _img_gen_elapsed = time.time() - _img_start_t
                if gcs_uri and _img_gen_elapsed < 20:  # Only run gecko if <20s spent on image gen
                    try:
                        result = gecko_evaluate(
                            prompt=state.get("key_selling_points", product),
                            media_uri=gcs_uri,
                            media_type="image",
                            project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
                            location="us-central1",
                        )
                        if isinstance(result, dict) and result.get("status") == "success":
                            fidelity_score = result.get("score", 0.0)
                        elif isinstance(result, (int, float)):
                            fidelity_score = float(result)
                        img_meta["fidelity_score"] = fidelity_score
                    except Exception as e:
                        logger.warning(f"[ImageGen] Gecko fidelity eval failed (non-fatal): {e}")
                elif gcs_uri:
                    logger.info(f"[ImageGen] Skipping Gecko eval — image gen took {_img_gen_elapsed:.0f}s (budget: 20s)")

                new_list = list(existing_imgs) + [img_meta]
                existing_imgs = new_list
                ref_type = shot.get("reference_type", "ASSET")
                fidelity_msg = (
                    f"Gecko fidelity: {fidelity_score:.2f}/1.00 "
                    f"({'PASS' if fidelity_score >= 0.7 else 'BELOW THRESHOLD'}) — "
                    f"reference type: {ref_type}"
                ) if fidelity_score is not None else f"reference type: {ref_type}"
                save_event = self._status_event(
                    ctx, f"Image {img_idx + 1}/{MAX_IMAGES} saved: {concept_name} | {fidelity_msg}"
                )
                # Emit fidelity narrative status
                if fidelity_score is not None:
                    yield self._status_event(
                        ctx,
                        f"Image fidelity analysis: {concept_name} scored {fidelity_score:.2f}/1.00 via Gecko embeddings — "
                        f"{'exceeds 0.70 threshold, approved as ' + ref_type + ' reference for video generation' if fidelity_score >= 0.7 else 'below threshold, will regenerate'}"
                    )
                save_event.actions.state_delta["img_artifact_keys"] = {"img_artifact_keys": new_list}
                # Reset failure counter on success (was pre-incremented)
                save_event.actions.state_delta[img_fail_key] = 0
                # Save as ADK artifact for inline display
                if ctx.artifact_service and image_bytes:
                    try:
                        version = await ctx.artifact_service.save_artifact(
                            app_name=ctx.app_name, user_id=ctx.user_id,
                            session_id=ctx.session.id, filename=artifact_key,
                            artifact=types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                        )
                        save_event.actions.artifact_delta[artifact_key] = version
                        logger.info(f"[ImageGen] Saved artifact: {artifact_key} v{version}")
                    except Exception as e:
                        logger.warning(f"[ImageGen] Failed to save artifact: {e}")
                yield save_event
            else:
                fail_event = self._status_event(ctx, f"Image {img_idx + 1} returned empty — retry {img_failures+1}/{MAX_IMG_RETRIES}.")
                fail_event.actions.state_delta[img_fail_key] = img_failures + 1
                yield fail_event

        except Exception as e:
            _elapsed = time.time() - _img_start_t if '_img_start_t' in dir() else 0
            logger.warning(f"[ImageGen] Failed after {_elapsed:.1f}s: {type(e).__name__}: {e}")
            fail_event = self._status_event(ctx, f"Image gen error ({_elapsed:.0f}s): {type(e).__name__}: {str(e)[:200]} — retry {img_failures+1}/{MAX_IMG_RETRIES}.")
            fail_event.actions.state_delta[img_fail_key] = img_failures + 1
            yield fail_event

    # -------------------------------------------------------------------------
    # AV_STUDIO — deterministic Veo commercial generation
    # -------------------------------------------------------------------------

    async def _generate_commercial_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate a commercial video using Veo with ASSET reference images.

        Uses the campaign's reference images (product ASSET, trend ASSET) to guide
        Veo generation for brand and trend consistency.

        Wave-safe: saves pending operations to state so AE can resume polling.
        """
        state = ctx.session.state
        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "target consumers")
        selling_points = state.get("key_selling_points", "")
        duration = state.get("commercial_duration", 15)
        brand = state.get("brand", "")
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")
        bucket_name = bucket.replace("gs://", "")

        veo_client = _get_media_client()
        clips_cache = state.get("_commercial_clips", {})

        pending_op = clips_cache.get("_pending_veo_op")

        if pending_op:
            yield self._status_event(ctx, f"Polling Veo commercial (resuming)...")
        else:
            yield self._status_event(ctx, f"Generating {duration}s commercial with ASSET references...")

        # Build Veo ASSET reference images from campaign images
        reference_images = self._build_veo_reference_images(state, bucket, gcs_folder)

        if reference_images:
            ref_details = []
            for ref_img in reference_images:
                uri = ref_img.image.gcs_uri if ref_img.image else "?"
                ref_details.append(f"ASSET: {uri[-60:]}")
            yield self._status_event(
                ctx, f"Veo references: {', '.join(ref_details)}"
            )
        else:
            yield self._status_event(ctx, "No reference images available — generating prompt-only commercial")

        # Get trend context for video prompt
        trend_context = self._get_trend_context(state)

        # Get ad headline and visual direction from creative phase
        ad_copies = state.get("final_select_ad_copies", {})
        if isinstance(ad_copies, dict):
            ad_copies = ad_copies.get("final_select_ad_copies", [])
        ad_headline = ""
        if ad_copies and isinstance(ad_copies[0], dict):
            ad_headline = ad_copies[0].get("headline", "")

        visual_concepts = state.get("final_select_visual_concepts", {})
        if isinstance(visual_concepts, dict):
            visual_concepts = visual_concepts.get("final_select_visual_concepts", [])
        visual_prompt_hint = ""
        if visual_concepts and isinstance(visual_concepts[0], dict):
            visual_prompt_hint = visual_concepts[0].get("prompt", "")

        # Build commercial prompt with brand + trend + creative context
        clip_prompt = self._build_commercial_prompt(
            product, audience, selling_points, duration, brand, trend_context,
            ad_headline=ad_headline, visual_prompt_hint=visual_prompt_hint,
        )

        gen_config = GenerateVideosConfig(
            aspect_ratio="16:9",
            number_of_videos=1,
            output_gcs_uri=bucket,
            reference_images=reference_images if reference_images else None,
        )

        try:
            if pending_op:
                from google.genai.types import GenerateVideosOperation
                logger.info(f"[DetAV] Resuming Veo operation: {pending_op}")
                try:
                    stub_op = GenerateVideosOperation(name=pending_op)
                    operation = veo_client.operations.get(operation=stub_op)
                except Exception as e:
                    logger.warning(f"[DetAV] Could not resume operation {pending_op}: {e}")
                    pending_op = None

            if not pending_op:
                logger.info(f"[DetAV] Submitting Veo: {len(reference_images)} reference images, prompt: {clip_prompt[:100]}...")
                operation = veo_client.models.generate_videos(
                    model=config.video_gen_model,
                    prompt=clip_prompt,
                    config=gen_config,
                )

                op_name = operation.name
                if op_name:
                    pre_save = self._status_event(ctx, f"Veo commercial submitted")
                    pre_save.actions.state_delta["_commercial_clips"] = {
                        "_pending_veo_op": op_name,
                    }
                    yield pre_save

            # Poll within AE wave budget
            start_time = time.time()
            while not operation.done:
                elapsed = time.time() - start_time
                if elapsed > AE_WAVE_POLL_BUDGET:
                    logger.info(f"[DetAV] Commercial still generating, will resume on next wave")
                    save_event = self._status_event(ctx, f"Commercial still generating — will resume")
                    save_event.actions.state_delta["_commercial_clips"] = {
                        "_pending_veo_op": operation.name,
                    }
                    yield save_event
                    return
                time.sleep(10)
                yield self._status_event(
                    ctx, f"Veo generating commercial... {int(elapsed)}s elapsed"
                )
                operation = veo_client.operations.get(operation)

            if operation.error:
                err_msg = str(operation.error)[:200]
                logger.warning(f"[DetAV] Veo error: {err_msg}")
                yield self._status_event(ctx, f"Veo failed: {err_msg[:100]}. Retrying without reference images...")
                # Retry without reference images on failure
                retry_config = GenerateVideosConfig(
                    aspect_ratio="16:9", number_of_videos=1, output_gcs_uri=bucket,
                )
                operation = veo_client.models.generate_videos(
                    model=config.video_gen_model, prompt=clip_prompt, config=retry_config,
                )
                if operation.name:
                    retry_save = self._status_event(ctx, f"Retrying commercial without references...")
                    retry_save.actions.state_delta["_commercial_clips"] = {
                        "_pending_veo_op": operation.name,
                    }
                    yield retry_save
                pending_op = None
                start_time = time.time()
                while not operation.done:
                    elapsed = time.time() - start_time
                    if elapsed > AE_WAVE_POLL_BUDGET:
                        save_event = self._status_event(ctx, "Retry still generating — will resume")
                        save_event.actions.state_delta["_commercial_clips"] = {
                            "_pending_veo_op": operation.name,
                        }
                        yield save_event
                        return
                    time.sleep(10)
                    yield self._status_event(
                        ctx, f"Veo retry... {int(elapsed)}s elapsed"
                    )
                    operation = veo_client.operations.get(operation)
                if operation.error:
                    yield self._status_event(ctx, f"Commercial failed after retry — skipping")
                    clear_event = self._status_event(ctx, "Clearing commercial state")
                    clear_event.actions.state_delta["_commercial_clips"] = {}
                    yield clear_event
                    return

            # Extract video URI
            video_uri = None
            if operation.result and operation.result.generated_videos:
                for video in operation.result.generated_videos:
                    if video.video and video.video.uri:
                        video_uri = video.video.uri
                        break

            if not video_uri:
                logger.warning(f"[DetAV] No video URI in Veo result")
                clear_event = self._status_event(ctx, f"Commercial returned empty — will retry")
                clear_event.actions.state_delta["_commercial_clips"] = {}
                yield clear_event
                return

            yield self._status_event(ctx, f"Commercial generated: {video_uri[-60:]}")
            final_gcs_uri = video_uri
            video_bytes = None

            # Copy to canonical name in GCS
            try:
                source_blob = video_uri.replace(f"gs://{bucket_name}/", "")
                video_bytes = download_blob(bucket_name=bucket_name, source_blob_name=source_blob)
                if gcs_folder and bucket:
                    art_blob = f"{gcs_folder}/commercial_{duration}s.mp4"
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                        tmp.write(video_bytes)
                        tmp_path = tmp.name
                    try:
                        upload_blob_to_gcs(source_file_name=tmp_path, destination_blob_name=art_blob)
                        final_gcs_uri = f"{bucket}/{art_blob}"
                    finally:
                        os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"[DetAV] Video copy failed (non-fatal): {e}")
            art_fname = f"commercial_{duration}s.mp4"

            if final_gcs_uri:
                commercial_data = {
                    "artifact_key": art_fname,
                    "gcs_uri": final_gcs_uri,
                    "metadata": {
                        "title": f"{duration}s commercial for {product}",
                        "scene_descriptions": [clip_prompt[:200]],
                        "total_clips": 1,
                        "duration_seconds": duration,
                        "narrative_arc": f"Trend-driven commercial for {brand} {product}",
                        "target_audience_appeal": f"Designed for {audience}",
                        "trend_connections": trend_context if trend_context else "N/A",
                        "has_audio": True,
                        "deterministic_av_studio": True,
                    },
                }
                event = self._status_event(ctx, f"Commercial generated: {duration}s, {final_gcs_uri[-60:]}")
                event.actions.state_delta["commercial_artifact"] = commercial_data
                event.actions.state_delta["vid_artifact_keys"] = {"vid_artifact_keys": [commercial_data]}
                event.actions.state_delta["_commercial_clips"] = {}
                if ctx.artifact_service and video_bytes:
                    try:
                        version = await ctx.artifact_service.save_artifact(
                            app_name=ctx.app_name, user_id=ctx.user_id,
                            session_id=ctx.session.id, filename=art_fname,
                            artifact=types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
                        )
                        event.actions.artifact_delta[art_fname] = version
                    except Exception as e:
                        logger.warning(f"[DetAV] Failed to save commercial artifact: {e}")
                yield event
                logger.info(f"[DetAV] Commercial saved: {final_gcs_uri}")
            else:
                # No video URI — clear state so retry can happen
                clear_event = self._status_event(ctx, "Commercial generation produced no output — will retry")
                clear_event.actions.state_delta["_commercial_clips"] = {}
                yield clear_event

        except Exception as e:
            logger.warning(f"[DetAV] Veo exception: {e}")
            yield self._status_event(ctx, f"Commercial generation error: {str(e)[:100]}")

    def _build_veo_reference_images(
        self, state: dict, bucket: str, gcs_folder: str,
    ) -> list:
        """Build ASSET-only Veo reference images from campaign image state.

        Veo only supports one reference type per call. All images are sent as
        ASSET type. Selects product ASSET + trend ASSET (or person ASSET fallback).
        """
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(img_keys, dict):
            img_list = img_keys.get("img_artifact_keys", [])
        else:
            img_list = img_keys if isinstance(img_keys, list) else []

        reference_images = []
        if not img_list or not gcs_folder or not bucket:
            return reference_images

        # Exclude skipped images (no actual GCS content)
        _valid = [m for m in img_list if isinstance(m, dict) and not m.get("skipped")]
        product_refs = [m for m in _valid if m.get("shot_type") == "product_asset"]
        trend_refs = [m for m in _valid if m.get("shot_type") == "trend_asset"]
        person_refs = [m for m in _valid if m.get("shot_type") == "person_asset"]

        # Product ASSET + Trend ASSET (fallback to person if no trend image)
        selected_refs = product_refs[:1] + trend_refs[:1]
        if not trend_refs and person_refs:
            selected_refs = product_refs[:1] + person_refs[:1]

        for img_meta in selected_refs:
            img_gcs_uri = img_meta.get("gcs_uri", "")
            if not img_gcs_uri:
                img_filename = img_meta.get("artifact_key", "")
                if not img_filename:
                    continue
                img_gcs_uri = f"{bucket}/{gcs_folder}/{img_filename}"
            reference_images.append(
                types.VideoGenerationReferenceImage(
                    image=types.Image(gcs_uri=img_gcs_uri, mime_type="image/png"),
                    reference_type=types.VideoGenerationReferenceType.ASSET,
                )
            )
            logger.info(
                f"[DetAV] Reference ASSET "
                f"(shot: {img_meta.get('shot_type', '?')}, "
                f"Gecko: {img_meta.get('fidelity_score', 'N/A')}) -> {img_gcs_uri}"
            )

        return reference_images

    def _get_trend_context(self, state: dict) -> str:
        """Extract trend titles from state for use in prompts."""
        search_trends = state.get("target_search_trends", {})
        search_title = ""
        if isinstance(search_trends, dict):
            st_list = search_trends.get("target_search_trends", [])
            if st_list:
                search_title = st_list[0].get("title", "") if isinstance(st_list[0], dict) else str(st_list[0])

        yt_trends = state.get("target_yt_trends", {})
        yt_title = ""
        if isinstance(yt_trends, dict):
            yt_list = yt_trends.get("target_yt_trends", [])
            if yt_list:
                yt_title = yt_list[0].get("title", "") if isinstance(yt_list[0], dict) else str(yt_list[0])

        trend_context = ""
        if search_title:
            trend_context += f'the "{search_title}" trend'
        if yt_title:
            trend_context += f' and the "{yt_title}" YouTube trend' if trend_context else f'the "{yt_title}" YouTube trend'
        return trend_context

    def _build_commercial_prompt(
        self, product: str, audience: str, selling_points: str, duration: int,
        brand: str = "", trend_context: str = "",
        ad_headline: str = "", visual_prompt_hint: str = "",
    ) -> str:
        """Build a detailed Veo prompt for the commercial."""
        trend_line = f"TREND INTEGRATION: Visually evoke {trend_context} through the aesthetic, setting, and mood. " if trend_context else ""
        concept_line = f"CREATIVE CONCEPT: \"{ad_headline}\" — " if ad_headline else ""
        visual_direction = f"VISUAL DIRECTION: {visual_prompt_hint[:300]}. " if visual_prompt_hint else ""
        return (
            f"A cinematic {duration}-second commercial for {brand} {product}. "
            f"{concept_line}"
            f"NARRATIVE: A {audience} discovers {brand} {product} — moment of genuine delight "
            f"as they experience the product — product in action showcasing its benefits — "
            f"close-up hero shot of the {brand} product packaging with branding visible. "
            f"{trend_line}"
            f"{visual_direction}"
            f"VISUAL STYLE: Premium commercial quality, warm golden-hour lighting, "
            f"shallow depth of field, smooth camera movements, cinematic color grading. "
            f"CAMERA: Start medium-wide, dolly in to close-up on product, "
            f"slow push-in to branded hero moment. Smooth transitions. "
            f"MOOD: Fresh, uplifting, naturally luxurious. "
            f"PRODUCT BRANDING: The {brand} name and product label must appear naturally in at least one shot. "
            f"{selling_points[:200]}. "
            f"SUPPRESS SUBTITLES. NO WATERMARKS."
        )

    # -------------------------------------------------------------------------
    # SAVE_REPORT
    # -------------------------------------------------------------------------

    async def _save_final_report(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Call save_final_report_tool directly — no LLM needed."""
        state = ctx.session.state
        processed_report = state.get("combined_final_cited_report", "")
        gcs_folder = state.get("gcs_folder", "")

        if not processed_report:
            # Even without a report, set final_report_with_citations to prevent infinite SAVE_REPORT loop
            skip_event = self._status_event(ctx, "No research report to save — skipping PDF generation.")
            skip_event.actions.state_delta["final_report_with_citations"] = "(No research report available)"
            yield skip_event
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
            brand=state.get("brand", ""),
            product=state.get("target_product", ""),
            audience=state.get("target_audience", ""),
            selling_points=state.get("key_selling_points", ""),
            target_search_trends=state.get("target_search_trends", ""),
            target_yt_trends=state.get("target_yt_trends", ""),
        )

        status = result.get("status", "failed")
        artifact_key = result.get("artifact_key", "")
        if status == "ok":
            # Persist via state_delta event (direct mutation doesn't survive AE invocations)
            report_event = self._status_event(
                ctx, f"Final campaign report saved as PDF: {artifact_key}"
            )
            # Enrich report with creative assets summary
            asset_summary = f"\n\n## Creative Assets\n- Images: {len(img_artifact_list)} generated"
            for img in img_artifact_list:
                if isinstance(img, dict):
                    asset_summary += f"\n  - {img.get('concept_name', img.get('artifact_key', '?'))}: Gecko {img.get('fidelity_score', 'N/A')}, type: {img.get('reference_type', 'N/A')}"
            if isinstance(commercial_artifact, dict) and commercial_artifact.get("gcs_uri"):
                asset_summary += f"\n- Commercial: {commercial_artifact['gcs_uri']}"
            if focus_group_evaluation:
                asset_summary += f"\n\n## Focus Group\n{str(focus_group_evaluation)[:500]}"

            report_event.actions.state_delta["final_report_with_citations"] = processed_report + asset_summary
            # Persist PDF artifact location in state for frontend access
            gcs_bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
            pdf_gcs_uri = f"{gcs_bucket}/{gcs_folder}/{artifact_key}" if gcs_folder else ""
            report_event.actions.state_delta["pdf_artifact"] = {
                "artifact_key": artifact_key,
                "gcs_uri": pdf_gcs_uri,
                "version": result.get("version"),
            }
            # Set artifact_delta so PDF appears inline in ADK web UI / GE
            version = result.get("version")
            if version is not None:
                report_event.actions.artifact_delta[artifact_key] = version
            yield report_event
        else:
            msg = f"Failed to save final report: {result.get('error', 'unknown')}"
            # Still set final_report_with_citations to prevent infinite SAVE_REPORT loop
            fail_event = self._status_event(ctx, msg)
            fail_event.actions.state_delta["final_report_with_citations"] = processed_report
            yield fail_event

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
