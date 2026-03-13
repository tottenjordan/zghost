"""CreativeProductionOrchestrator — deterministic BaseAgent for the creative pipeline.

Sequences ad creative generation, AV studio commercial production, and
commercial quality evaluation with a Gecko-based QA loop.

Pipeline stages:
  AD_CREATIVE   -> ad_content_generator_agent (ad copy + visual concepts + image/video gen)
  AV_STUDIO     -> av_editing_studio_agent (commercial production)
  COMMERCIAL_QA -> commercial_qa_agent (Gecko + Gemini video analysis)

If the commercial QA fails, the orchestrator retries AV_STUDIO up to
MAX_COMMERCIAL_RETRIES times before continuing.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from google.genai import types
from google.adk.agents.base_agent import BaseAgent, BaseAgentState
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing
from google.adk.utils.feature_decorator import experimental

from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from ...skills.focus_group.tools import analyze_commercial_video
from .tools import evaluate_media_fidelity

logger = logging.getLogger("google_adk." + __name__)

MAX_COMMERCIAL_RETRIES = 2

# --- Commercial QA Agent ---
commercial_qa_agent = Agent(
    model=config.critic_model,
    name="commercial_qa_agent",
    description="Evaluates commercial video quality using Gemini vision and Gecko fidelity scoring.",
    instruction="""You evaluate the commercial video quality using two techniques.

## Steps:

1. Call `analyze_commercial_video` to get Gemini's detailed visual analysis of the commercial.
2. Read `commercial_artifact` from session state. Extract the GCS URI from `commercial_artifact["gcs_uri"]`.
3. Call `evaluate_media_fidelity` with:
   - media_uri: the commercial's GCS URI
   - ground_truth_description: describe the target product using `{target_product}` and `{key_selling_points}`
   - media_type: "video"
4. Based on BOTH the visual analysis AND the fidelity score, write your assessment:

If fidelity_score >= 0.7 AND the visual analysis shows acceptable quality:
   Write: "COMMERCIAL QA: PASS" followed by a brief summary of strengths.

If fidelity_score < 0.7 OR the visual analysis shows significant quality issues:
   Write: "COMMERCIAL QA: FAIL" followed by specific issues that need to be addressed.

Be concise. Focus on actionable quality feedback.""",
    tools=[analyze_commercial_video, evaluate_media_fidelity],
    output_key="commercial_qa_result",
    generate_content_config=types.GenerateContentConfig(temperature=0.3),
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024)
    ),
    before_model_callback=callbacks.rate_limit_callback,
)


CREATIVE_STAGES = [
    ("AD_CREATIVE", "ad_content_generator_agent", "Generating ad copy and visual creatives..."),
    ("AV_STUDIO", "av_editing_studio_agent", "Producing commercial in AV editing studio..."),
    ("COMMERCIAL_QA", "commercial_qa_agent", "Evaluating commercial quality with Gecko..."),
]


@experimental
class CreativeProductionState(BaseAgentState):
    """Persisted state for AE resumability."""
    current_stage_index: int = 0
    av_studio_attempts: int = 0


class CreativeProductionOrchestrator(BaseAgent):
    """Deterministic orchestrator for the creative production pipeline.

    Sequences ad creative generation, AV studio commercial production,
    and commercial QA with Gecko-based quality evaluation. If the QA
    fails, retries AV studio up to MAX_COMMERCIAL_RETRIES times.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self.sub_agents:
            return

        state = ctx.session.state
        agent_state = self._load_agent_state(ctx, CreativeProductionState)
        start_index = agent_state.current_stage_index if agent_state else 0
        av_attempts = agent_state.av_studio_attempts if agent_state else 0
        resuming = agent_state is not None
        pause_invocation = False

        i = start_index
        while i < len(CREATIVE_STAGES):
            stage_name, agent_name, status_msg = CREATIVE_STAGES[i]

            # Skip AD_CREATIVE if images already generated
            if stage_name == "AD_CREATIVE" and not resuming:
                img_keys = state.get("img_artifact_keys", {})
                if isinstance(img_keys, dict):
                    img_keys = img_keys.get("img_artifact_keys", [])
                if img_keys and len(img_keys) >= 2:
                    logger.info("[CreativeProduction] Skipping AD_CREATIVE — images already exist")
                    i += 1
                    continue

            # Skip AV_STUDIO if commercial already exists (and not retrying)
            if stage_name == "AV_STUDIO" and not resuming and av_attempts == 0:
                if state.get("commercial_artifact"):
                    logger.info("[CreativeProduction] Skipping AV_STUDIO — commercial already exists")
                    i += 1
                    continue

            if not resuming:
                # Persist state for AE resume
                if ctx.is_resumable:
                    ps = CreativeProductionState(
                        current_stage_index=i, av_studio_attempts=av_attempts
                    )
                    ctx.set_agent_state(self.name, agent_state=ps)
                    yield self._create_agent_state_event(ctx)

                yield self._status_event(ctx, status_msg)

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

            # After COMMERCIAL_QA, check if retry is needed
            if stage_name == "COMMERCIAL_QA":
                qa_result = str(state.get("commercial_qa_result", ""))
                if "FAIL" in qa_result and av_attempts < MAX_COMMERCIAL_RETRIES:
                    av_attempts += 1
                    state["commercial_artifact"] = ""
                    state["commercial_qa_result"] = ""
                    yield self._status_event(
                        ctx,
                        f"Commercial QA failed. Retrying AV studio (attempt {av_attempts + 1}/{MAX_COMMERCIAL_RETRIES + 1})...",
                    )
                    i = 1  # Jump back to AV_STUDIO
                    resuming = False
                    continue

            resuming = False
            i += 1

        # Mark complete
        if ctx.is_resumable:
            ctx.set_agent_state(self.name, end_of_agent=True)
            yield self._create_agent_state_event(ctx)

    def _get_sub_agent(self, name: str):
        for agent in self.sub_agents:
            if agent.name == name:
                return agent
        return None

    def _status_event(self, ctx: InvocationContext, message: str) -> Event:
        logger.info(f"[CreativeProduction] {message}")
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
