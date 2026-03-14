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
import tempfile
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
from ...shared_libraries.utils import upload_blob_to_gcs
from ...shared_libraries import callbacks
from ...shared_libraries.fidelity_eval.gecko import evaluate as gecko_evaluate
from ...skills.focus_group.tools import analyze_commercial_video
from .tools import evaluate_media_fidelity

logger = logging.getLogger("google_adk." + __name__)

MAX_COMMERCIAL_RETRIES = 2
AV_STUDIO_MAX_RUNS = 3  # Max AV_STUDIO invocations before deterministic commercial
AE_WAVE_POLL_BUDGET = 45  # seconds to poll Veo within a single AE wave

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

        # If enough images exist (2), go to AV_STUDIO
        if img_keys and len(img_keys) >= 2:
            return 2  # AV_STUDIO
        # If some images exist but < 2, keep generating
        if img_keys and len(img_keys) >= 1:
            return 1  # IMAGE_GEN (generate more)
        # If ad copies exist (with or without visual concepts), run IMAGE_GEN
        # IMAGE_GEN will fall back to ad copy descriptions if no visual concepts
        if ad_copies:
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

            # AV_STUDIO: deterministic multi-clip commercial (no LLM agent)
            if stage_name == "AV_STUDIO":
                # Don't increment av_runs if we're just polling a pending Veo operation
                clips_cache = state.get("_commercial_clips", {})
                has_pending_op = any(k.startswith("_pending") for k in clips_cache)

                if not has_pending_op:
                    av_runs = state.get("_av_studio_runs", 0) + 1
                    track_event = self._status_event(
                        ctx, f"Deterministic AV studio attempt {av_runs}/{AV_STUDIO_MAX_RUNS}..."
                    )
                    track_event.actions.state_delta["_av_studio_runs"] = av_runs
                    yield track_event
                else:
                    av_runs = state.get("_av_studio_runs", 0)
                    yield self._status_event(ctx, f"Resuming Veo clip generation (attempt {av_runs}/{AV_STUDIO_MAX_RUNS})...")

                commercial_generated = False
                veo_still_pending = False
                async for event in self._generate_commercial_deterministic(ctx):
                    yield event
                    # Check if this event saved commercial_artifact via state_delta
                    if "commercial_artifact" in event.actions.state_delta:
                        commercial_generated = True
                    # Check if a pending Veo op was saved (still generating)
                    clips_delta = event.actions.state_delta.get("_commercial_clips", {})
                    if clips_delta and clips_delta.get("_pending_veo_op"):
                        veo_still_pending = True

                if commercial_generated:
                    i += 1  # Move to COMMERCIAL_QA
                elif veo_still_pending:
                    # Veo is actively generating — do NOT count as failed attempt
                    pass  # Will resume polling on next wave
                elif av_runs >= AV_STUDIO_MAX_RUNS:
                    yield self._status_event(ctx, "All AV studio attempts exhausted — skipping commercial QA")
                    i = len(CREATIVE_STAGES)  # Skip to end
                # else: will retry on next wave
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
        """Generate ONE campaign image per wave using Imagen API.

        Uses generate_images() which is synchronous but faster than Gemini
        generate_content with IMAGE modality. Outputs directly to GCS.
        """
        state = ctx.session.state
        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "consumers")
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")
        MAX_IMAGES = 2

        existing_imgs = state.get("img_artifact_keys", {})
        if isinstance(existing_imgs, dict):
            existing_imgs = existing_imgs.get("img_artifact_keys", [])
        if not isinstance(existing_imgs, list):
            existing_imgs = []
        already_generated = len(existing_imgs)

        if already_generated >= MAX_IMAGES:
            yield self._status_event(ctx, f"All {MAX_IMAGES} images already generated.")
            return

        # Build concept list (fallback chain)
        vis_concepts = state.get("final_select_vis_concepts", {})
        if isinstance(vis_concepts, dict):
            vis_concepts = vis_concepts.get("final_select_vis_concepts", [])
        if not vis_concepts:
            ad_copies = state.get("final_select_ad_copies", {})
            if isinstance(ad_copies, dict):
                ad_copies = ad_copies.get("final_select_ad_copies", [])
            ad_critique = state.get("ad_copy_critique", "")
            if ad_copies:
                vis_concepts = [
                    {"concept_name": f"ad_copy_{i+1}", "description": str(c)[:300]}
                    for i, c in enumerate(ad_copies[:MAX_IMAGES])
                ]
            elif ad_critique:
                vis_concepts = [{"concept_name": "campaign_visual", "description": str(ad_critique)[:300]}]
            else:
                vis_concepts = [{"concept_name": "product_hero", "description": f"Hero shot of {product}"}]

        generic_concepts = [
            {"concept_name": "lifestyle_shot", "description": f"{product} in a natural lifestyle setting"},
            {"concept_name": "hero_product", "description": f"Studio hero shot of {product}"},
        ]
        while len(vis_concepts) < MAX_IMAGES:
            vis_concepts.append(generic_concepts[len(vis_concepts) % len(generic_concepts)])

        concept = vis_concepts[already_generated] if already_generated < len(vis_concepts) else vis_concepts[0]
        concept_name = concept.get("concept_name", "concept") if isinstance(concept, dict) else "concept"
        description = concept.get("description", str(concept)) if isinstance(concept, dict) else str(concept)

        prompt = (
            f"Professional advertising photography for {product}. "
            f"Concept: {description[:300]}. "
            f"Target audience: {audience}. "
            f"High quality, cinematic lighting, lifestyle aesthetic. "
            f"No text, no logos, no watermarks."
        )

        yield self._status_event(ctx, f"Generating image {already_generated + 1}/{MAX_IMAGES}...")

        try:
            img_client = genai.Client(vertexai=True)

            # Use Imagen API — outputs directly to GCS, typically faster
            from google.genai.types import GenerateImagesConfig as ImgGenConfig
            response = img_client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt,
                config=ImgGenConfig(
                    number_of_images=1,
                    output_gcs_uri=bucket,
                ),
            )

            if response and response.generated_images:
                gen_image = response.generated_images[0]
                safe_name = concept_name.replace(",", "").replace(" ", "_")
                artifact_key = f"{safe_name}_0.png"
                gcs_uri = ""

                if gen_image.image and gen_image.image.gcs_uri:
                    gcs_uri = gen_image.image.gcs_uri

                    # Copy to campaign folder
                    if bucket and gcs_folder:
                        try:
                            from google.cloud import storage as gcs_storage
                            storage_client = gcs_storage.Client()
                            bucket_name = bucket.replace("gs://", "")
                            src_parts = gcs_uri.replace("gs://", "").split("/", 1)
                            src_bucket = storage_client.bucket(src_parts[0])
                            src_blob = src_bucket.blob(src_parts[1])
                            dst_bucket = storage_client.bucket(bucket_name)
                            src_bucket.copy_blob(src_blob, dst_bucket, os.path.join(gcs_folder, artifact_key))
                        except Exception as e:
                            logger.warning(f"[ImageGen] GCS copy failed: {e}")

                elif gen_image.image and gen_image.image.image_bytes:
                    # Fallback: image returned as bytes
                    image_bytes = gen_image.image.image_bytes
                    if bucket and gcs_folder:
                        from .tools import upload_blob_to_gcs
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

                img_meta = {
                    "artifact_key": artifact_key,
                    "img_prompt": prompt[:500],
                    "concept": concept_name,
                    "headline": "",
                    "caption": "",
                    "auto_saved": True,
                }
                if gcs_uri:
                    img_meta["gcs_uri"] = gcs_uri

                # Gecko fidelity (best-effort)
                if bucket and gcs_folder:
                    try:
                        fidelity_score = gecko_evaluate(
                            prompt=state.get("key_selling_points", product),
                            media_uri=f"{bucket}/{gcs_folder}/{artifact_key}",
                            media_type="image",
                        )
                        img_meta["fidelity_score"] = fidelity_score
                    except Exception:
                        pass

                new_list = list(existing_imgs) + [img_meta]
                save_event = self._status_event(ctx, f"Image saved: {artifact_key}")
                save_event.actions.state_delta["img_artifact_keys"] = {"img_artifact_keys": new_list}
                yield save_event
                return

            yield self._status_event(ctx, "Image gen returned empty — will retry next wave.")

        except Exception as e:
            logger.warning(f"[ImageGen] Failed: {e}")
            yield self._status_event(ctx, f"Image gen failed: {str(e)[:100]} — will retry.")

    async def _generate_commercial_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate a commercial deterministically using direct Veo SDK calls.

        Uses a wave-safe approach: submit Veo operation, save operation name
        to state, poll on subsequent waves until complete. Uses campaign images
        as first-frame conditioning when available.
        """
        state = ctx.session.state
        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "target consumers")
        selling_points = state.get("key_selling_points", "")
        duration = state.get("commercial_duration", 15)
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")
        bucket_name = bucket.replace("gs://", "")

        veo_client = genai.Client(vertexai=True)
        clips_cache = state.get("_commercial_clips", {})

        # Check for pending Veo operation from previous wave
        pending_op = clips_cache.get("_pending_veo_op")
        if pending_op:
            yield self._status_event(ctx, "Polling Veo commercial (resuming from previous wave)...")
        else:
            yield self._status_event(ctx, "Submitting commercial to Veo...")

        # Get first campaign image for first-frame conditioning
        first_frame_uri = ""
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(img_keys, dict):
            img_list = img_keys.get("img_artifact_keys", [])
        else:
            img_list = img_keys if isinstance(img_keys, list) else []
        if img_list and gcs_folder and bucket:
            first_img = img_list[0]
            img_filename = first_img.get("artifact_key", "") if isinstance(first_img, dict) else str(first_img)
            if img_filename:
                first_frame_uri = f"{bucket}/{gcs_folder}/{img_filename}"

        # Build a detailed Veo prompt
        prompt = self._build_commercial_prompt(product, audience, selling_points, duration)

        try:
            gen_config = GenerateVideosConfig(
                aspect_ratio="16:9",
                number_of_videos=1,
                output_gcs_uri=bucket,
            )

            if pending_op:
                # Resume polling an already-submitted operation
                from google.genai.types import GenerateVideosOperation
                logger.info(f"[DetAV] Resuming Veo operation: {pending_op}")
                try:
                    stub_op = GenerateVideosOperation(name=pending_op)
                    operation = veo_client.operations.get(operation=stub_op)
                except Exception as e:
                    logger.warning(f"[DetAV] Could not resume operation {pending_op}: {e}")
                    pending_op = None

            if not pending_op:
                # Submit new Veo operation
                if first_frame_uri:
                    first_frame_image = types.Image(
                        gcs_uri=first_frame_uri, mime_type="image/png"
                    )
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

                # CRITICAL: Save operation name to state BEFORE polling
                # If AE wave times out during polling, we can resume next wave
                op_name = operation.name
                if op_name:
                    pre_save = self._status_event(ctx, f"Veo operation submitted: {op_name[:40]}...")
                    pre_save.actions.state_delta["_commercial_clips"] = {"_pending_veo_op": op_name}
                    yield pre_save

            # Poll within AE wave budget
            start_time = time.time()
            while not operation.done:
                if time.time() - start_time > AE_WAVE_POLL_BUDGET:
                    op_name = operation.name
                    logger.info(f"[DetAV] Veo clip still generating, will resume: {op_name}")
                    save_event = self._status_event(ctx, "Commercial still generating — will resume on next wave")
                    save_event.actions.state_delta["_commercial_clips"] = {"_pending_veo_op": op_name}
                    yield save_event
                    return
                time.sleep(10)
                operation = veo_client.operations.get(operation)

            if operation.error:
                logger.warning(f"[DetAV] Veo error: {operation.error}")
                # Retry without first-frame if it failed with one
                if first_frame_uri and not pending_op:
                    logger.info("[DetAV] Retrying without first-frame conditioning...")
                    operation = veo_client.models.generate_videos(
                        model=config.video_gen_model,
                        prompt=prompt,
                        config=gen_config,
                    )
                    # Save this new op too
                    if operation.name:
                        pre_save2 = self._status_event(ctx, "Retrying Veo without first-frame...")
                        pre_save2.actions.state_delta["_commercial_clips"] = {"_pending_veo_op": operation.name}
                        yield pre_save2

                    start_time = time.time()
                    while not operation.done:
                        if time.time() - start_time > AE_WAVE_POLL_BUDGET:
                            save_event = self._status_event(ctx, "Retry still generating — will resume")
                            save_event.actions.state_delta["_commercial_clips"] = {"_pending_veo_op": operation.name}
                            yield save_event
                            return
                        time.sleep(10)
                        operation = veo_client.operations.get(operation)
                    if operation.error:
                        yield self._status_event(ctx, "Commercial generation failed after retry")
                        return
                else:
                    yield self._status_event(ctx, "Commercial generation failed")
                    return

            # Success — extract video URI
            clip_uri = None
            if operation.result and operation.result.generated_videos:
                for video in operation.result.generated_videos:
                    if video.video and video.video.uri:
                        clip_uri = video.video.uri
                        break

            if clip_uri:
                commercial_data = {
                    "artifact_key": f"commercial_{duration}s.mp4",
                    "gcs_uri": clip_uri,
                    "metadata": {
                        "title": f"{duration}s commercial for {product}",
                        "scene_descriptions": [
                            f"Opening: Character discovers {product}",
                            f"Middle: Product in use, sensory delight",
                            f"Closing: Product hero shot",
                        ],
                        "total_clips": 1,
                        "duration_seconds": duration,
                        "narrative_arc": f"Discovery -> delight -> product reveal for {product}",
                        "target_audience_appeal": f"Designed for {audience}",
                        "deterministic_av_studio": True,
                    },
                }
                event = self._status_event(ctx, f"Commercial generated: {clip_uri}")
                event.actions.state_delta["commercial_artifact"] = commercial_data
                event.actions.state_delta["_commercial_clips"] = {}
                yield event
                logger.info(f"[DetAV] Commercial saved: {clip_uri}")
            else:
                # CRITICAL: Clear pending op so retry counter can increment
                clear_event = self._status_event(ctx, "Veo completed but no video URI returned — will retry")
                clear_event.actions.state_delta["_commercial_clips"] = {}
                yield clear_event

        except Exception as e:
            logger.warning(f"[DetAV] Veo exception: {e}")
            yield self._status_event(ctx, f"Commercial generation error: {str(e)[:100]}")

    def _build_commercial_prompt(
        self, product: str, audience: str, selling_points: str, duration: int,
    ) -> str:
        """Build a detailed Veo prompt for the commercial."""
        return (
            f"A cinematic {duration}-second commercial for {product}. "
            f"NARRATIVE: A {audience} discovers {product} — moment of genuine delight "
            f"as they experience the product — product in action showcasing its benefits — "
            f"hero shot with satisfied expression. "
            f"VISUAL STYLE: Premium commercial quality, warm golden-hour lighting, "
            f"shallow depth of field, smooth camera movements, cinematic color grading. "
            f"CAMERA: Start medium-wide, dolly in to close-up on product interaction, "
            f"slow push-in to hero moment. Smooth transitions. "
            f"MOOD: Fresh, uplifting, naturally luxurious. "
            f"{selling_points[:200]}. "
            f"SUPPRESS SUBTITLES. NO TEXT ON SCREEN. NO WATERMARKS. NO LOGOS."
        )

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
