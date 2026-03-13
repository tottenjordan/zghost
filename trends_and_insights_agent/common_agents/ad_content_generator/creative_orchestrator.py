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
import os
import time
from typing import AsyncGenerator

from google import genai
from google.genai import types
from google.genai.types import GenerateVideosConfig
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
AV_STUDIO_MAX_RUNS = 3  # Max AV_STUDIO invocations before fallback commercial

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
    ("IMAGE_GEN", "standalone_image_generator", "Generating campaign images from visual concepts..."),
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

    def _determine_start_index(self, ctx: InvocationContext) -> int:
        """Determine start index from session state (works across AE invocations)."""
        state = ctx.session.state

        # If commercial QA passed AND commercial actually exists, all done
        qa_result = state.get("commercial_qa_result", "")
        has_commercial = bool(state.get("commercial_artifact"))
        if qa_result and "PASS" in str(qa_result) and has_commercial:
            return len(CREATIVE_STAGES)  # All done

        # If commercial exists but no QA yet, go to QA
        if has_commercial:
            return 3  # COMMERCIAL_QA

        # Check creative assets
        ad_copies = state.get("final_select_ad_copies", {})
        vis_concepts = state.get("final_select_vis_concepts", {})
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(ad_copies, dict):
            ad_copies = ad_copies.get("final_select_ad_copies", [])
        if isinstance(vis_concepts, dict):
            vis_concepts = vis_concepts.get("final_select_vis_concepts", [])
        if isinstance(img_keys, dict):
            img_keys = img_keys.get("img_artifact_keys", [])

        # If concepts + images exist, check if AV_STUDIO is exhausted
        if ad_copies and vis_concepts and img_keys and len(img_keys) >= 1:
            av_runs = state.get("_av_studio_runs", 0)
            if av_runs >= AV_STUDIO_MAX_RUNS:
                return len(CREATIVE_STAGES)  # Skip to end (fallback will handle)
            return 2  # AV_STUDIO
        # If concepts exist but no images, run IMAGE_GEN stage
        if ad_copies and vis_concepts:
            return 1  # IMAGE_GEN

        return 0  # Start from AD_CREATIVE

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self.sub_agents:
            return

        state = ctx.session.state
        # Determine start from session state (robust across AE invocations)
        start_index = self._determine_start_index(ctx)
        av_attempts = 0
        pause_invocation = False

        logger.info(f"[CreativeProduction] Starting from stage index {start_index} (of {len(CREATIVE_STAGES)})")

        i = start_index
        while i < len(CREATIVE_STAGES):
            stage_name, agent_name, status_msg = CREATIVE_STAGES[i]

            # Persist state for AE resume
            if ctx.is_resumable:
                ps = CreativeProductionState(
                    current_stage_index=i, av_studio_attempts=av_attempts
                )
                ctx.set_agent_state(self.name, agent_state=ps)
                yield self._create_agent_state_event(ctx)

            yield self._status_event(ctx, status_msg)

            # IMAGE_GEN: deterministic image generation (no LLM agent)
            if stage_name == "IMAGE_GEN":
                async for event in self._generate_images_deterministic(ctx):
                    yield event
                i += 1
                continue

            # Track AV_STUDIO invocations via state_delta
            if stage_name == "AV_STUDIO":
                av_runs = state.get("_av_studio_runs", 0) + 1
                track_event = self._status_event(
                    ctx, f"AV studio attempt {av_runs}/{AV_STUDIO_MAX_RUNS}..."
                )
                track_event.actions.state_delta["_av_studio_runs"] = av_runs
                yield track_event
                if av_runs > AV_STUDIO_MAX_RUNS:
                    # AV studio exhausted — generate fallback commercial
                    async for event in self._generate_fallback_commercial(ctx):
                        yield event
                    i += 1  # Skip to COMMERCIAL_QA (or end)
                    continue

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
                    # Clear via state_delta event (direct mutation doesn't persist on AE)
                    retry_event = self._status_event(
                        ctx,
                        f"Commercial QA failed. Retrying AV studio (attempt {av_attempts + 1}/{MAX_COMMERCIAL_RETRIES + 1})...",
                    )
                    retry_event.actions.state_delta["commercial_artifact"] = ""
                    retry_event.actions.state_delta["commercial_qa_result"] = ""
                    yield retry_event
                    i = 2  # Jump back to AV_STUDIO
                    continue

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

    async def _generate_images_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate campaign images deterministically without an LLM agent.

        Called as the IMAGE_GEN stage. Reads visual concepts from state and
        generates images directly via the Gemini image gen SDK.
        """
        state = ctx.session.state
        vis_concepts = state.get("final_select_vis_concepts", {})
        if isinstance(vis_concepts, dict):
            vis_concepts = vis_concepts.get("final_select_vis_concepts", [])

        if not vis_concepts:
            yield self._status_event(ctx, "No visual concepts found — skipping image generation.")
            return

        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "consumers")
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")

        img_client = genai.Client(vertexai=True)
        generated_images = []

        for i, concept in enumerate(vis_concepts[:2]):  # Generate max 2 images
            concept_name = concept.get("concept_name", f"concept_{i}") if isinstance(concept, dict) else f"concept_{i}"
            description = concept.get("description", str(concept)) if isinstance(concept, dict) else str(concept)

            prompt = (
                f"Professional campaign photography for {product}. "
                f"Visual concept: {description[:300]}. "
                f"Target audience: {audience}. "
                f"High quality, cinematic lighting, lifestyle aesthetic. "
                f"No text, no logos, no watermarks."
            )
            yield self._status_event(ctx, f"Generating image {i + 1}/2: {concept_name}...")

            try:
                response = None
                for attempt in range(3):
                    try:
                        response = img_client.models.generate_content(
                            model=config.image_gen_model,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_modalities=["IMAGE"],
                            ),
                        )
                        break
                    except Exception as gen_err:
                        err_str = str(gen_err)
                        if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < 2:
                            wait = 15 * (attempt + 1)
                            logger.warning(f"Image gen rate limited, waiting {wait}s")
                            time.sleep(wait)
                        else:
                            raise

                if not response or not response.candidates or not response.candidates[0].content.parts:
                    logger.warning(f"[ImageGen] No image in response for concept {i}")
                    continue

                # Save image to GCS
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        safe_name = concept_name.replace(",", "").replace(" ", "_")
                        artifact_key = f"{safe_name}_0.png"

                        if bucket and gcs_folder:
                            from .tools import upload_blob_to_gcs
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                                tmp.write(image_bytes)
                                tmp_path = tmp.name
                            try:
                                upload_blob_to_gcs(
                                    source_file_name=tmp_path,
                                    destination_blob_name=os.path.join(gcs_folder, artifact_key),
                                )
                            finally:
                                os.unlink(tmp_path)

                        # Save artifact via artifact_service if available
                        if ctx.artifact_service:
                            await ctx.artifact_service.save_artifact(
                                app_name=ctx.app_name,
                                user_id=ctx.user_id,
                                session_id=ctx.session.id,
                                filename=artifact_key,
                                artifact=types.Part.from_bytes(
                                    data=image_bytes, mime_type="image/png"
                                ),
                            )

                        img_meta = {
                            "artifact_key": artifact_key,
                            "img_prompt": prompt[:500],
                            "concept": concept_name,
                            "headline": "",
                            "caption": "",
                            "auto_saved": True,
                        }
                        generated_images.append(img_meta)
                        logger.info(f"[ImageGen] Generated: {artifact_key}")

                        # Persist IMMEDIATELY after each image via state_delta
                        # (AE wave may end before the next image generates)
                        existing = state.get("img_artifact_keys", {"img_artifact_keys": []})
                        prev_list = list(existing.get("img_artifact_keys", []) if isinstance(existing, dict) else existing)
                        existing_keys = {item.get("artifact_key") for item in prev_list if isinstance(item, dict)}
                        if artifact_key not in existing_keys:
                            prev_list.append(img_meta)
                        save_event = self._status_event(
                            ctx, f"Image {len(generated_images)} saved: {artifact_key}"
                        )
                        save_event.actions.state_delta["img_artifact_keys"] = {"img_artifact_keys": list(prev_list)}
                        yield save_event
                        break  # Only need first image part

            except Exception as e:
                logger.warning(f"[ImageGen] Failed for concept {i}: {e}")
                yield self._status_event(ctx, f"Image generation failed for {concept_name}: {str(e)[:100]}")

        if generated_images:
            yield self._status_event(ctx, f"Generated {len(generated_images)} campaign images successfully.")
        else:
            yield self._status_event(ctx, "No images generated — will retry on next wave.")

    async def _generate_fallback_commercial(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate a simple Veo video as a fallback commercial.

        Called when the AV studio fails to produce a commercial after
        AV_STUDIO_MAX_RUNS attempts. Uses the first campaign image as
        a first-frame reference and generates a single Veo clip.
        """
        state = ctx.session.state
        yield self._status_event(ctx, "AV studio exhausted. Generating fallback commercial with Veo...")

        # Get campaign context
        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "target consumers")
        selling_points = state.get("key_selling_points", "")
        duration = state.get("commercial_duration", 15)

        # Get first campaign image for first-frame conditioning
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(img_keys, dict):
            img_list = img_keys.get("img_artifact_keys", [])
        else:
            img_list = img_keys if isinstance(img_keys, list) else []

        first_frame_image = None
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")
        if img_list and gcs_folder and bucket:
            first_img = img_list[0]
            img_filename = first_img.get("artifact_key", "") if isinstance(first_img, dict) else str(first_img)
            if img_filename:
                gcs_uri = f"{bucket}/{gcs_folder}/{img_filename}"
                first_frame_image = types.Image(gcs_uri=gcs_uri, mime_type="image/png")
                logger.info(f"[FallbackCommercial] Using first-frame: {gcs_uri}")

        # Build prompt
        prompt = (
            f"A cinematic {duration}-second commercial for {product}. "
            f"Targeting {audience}. "
            f"Key features: {selling_points}. "
            f"Smooth camera movement, warm natural lighting, lifestyle setting. "
            f"Product prominently featured. No text or logos in the video."
        )

        try:
            veo_client = genai.Client(vertexai=True)
            gen_config = GenerateVideosConfig(
                aspect_ratio="16:9",
                number_of_videos=1,
                output_gcs_uri=bucket,
            )
            if first_frame_image:
                operation = veo_client.models.generate_videos(
                    model=config.video_gen_model,
                    prompt=prompt,
                    image=first_frame_image,
                    config=gen_config,
                )
            else:
                operation = veo_client.models.generate_videos(
                    model=config.video_gen_model,
                    prompt=prompt,
                    config=gen_config,
                )

            while not operation.done:
                time.sleep(15)
                operation = veo_client.operations.get(operation)

            if operation.error:
                logger.warning(f"[FallbackCommercial] Veo error: {operation.error}")
                yield self._status_event(ctx, f"Fallback commercial generation failed: {operation.error}")
                return

            if operation.result and operation.result.generated_videos:
                video = operation.result.generated_videos[0]
                if video.video and video.video.uri:
                    video_uri = video.video.uri
                    commercial_data = {
                        "artifact_key": f"commercial_{duration}s.mp4",
                        "gcs_uri": video_uri,
                        "metadata": {
                            "title": f"Fallback {duration}s commercial for {product}",
                            "scene_descriptions": [f"Single-shot lifestyle commercial for {product}"],
                            "total_clips": 1,
                            "duration_seconds": duration,
                            "narrative_arc": f"Simple product showcase for {product}",
                            "target_audience_appeal": f"Designed for {audience}",
                            "fallback": True,
                        },
                    }
                    event = self._status_event(ctx, f"Fallback commercial generated: {video_uri}")
                    event.actions.state_delta["commercial_artifact"] = commercial_data
                    yield event
                    logger.info(f"[FallbackCommercial] Commercial saved: {video_uri}")
                    return

            yield self._status_event(ctx, "Fallback commercial: no video in Veo response")

        except Exception as e:
            logger.warning(f"[FallbackCommercial] Exception: {e}")
            yield self._status_event(ctx, f"Fallback commercial failed: {str(e)[:200]}")

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
