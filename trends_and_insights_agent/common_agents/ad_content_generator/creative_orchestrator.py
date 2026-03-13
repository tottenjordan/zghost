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

import asyncio
import logging
import os
import subprocess
import tempfile
import time
import uuid
from typing import AsyncGenerator

import cv2
from google import genai
from google.genai import types
from google.genai.types import GenerateVideosConfig
from google.cloud import storage
from google.adk.agents.base_agent import BaseAgent, BaseAgentState
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing
from google.adk.utils.feature_decorator import experimental

from ...shared_libraries.config import config
from ...shared_libraries.utils import upload_blob_to_gcs, download_blob, download_image_from_gcs
from ...shared_libraries import callbacks
from ...skills.focus_group.tools import analyze_commercial_video
from .tools import evaluate_media_fidelity

logger = logging.getLogger("google_adk." + __name__)

MAX_COMMERCIAL_RETRIES = 2
AV_STUDIO_MAX_RUNS = 3  # Max AV_STUDIO invocations before deterministic commercial
MAX_VEO_POLL_SECONDS = 300  # 5 min per clip
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

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

        # If concepts + images exist, go to AV_STUDIO
        # (the _run_async_impl handler will trigger fallback if exhausted)
        if ad_copies and vis_concepts and img_keys and len(img_keys) >= 1:
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

            # AV_STUDIO: deterministic multi-clip commercial (no LLM agent)
            if stage_name == "AV_STUDIO":
                av_runs = state.get("_av_studio_runs", 0) + 1
                track_event = self._status_event(
                    ctx, f"Deterministic AV studio attempt {av_runs}/{AV_STUDIO_MAX_RUNS}..."
                )
                track_event.actions.state_delta["_av_studio_runs"] = av_runs
                yield track_event

                commercial_generated = False
                async for event in self._generate_commercial_deterministic(ctx):
                    yield event
                    # Check if this event saved commercial_artifact via state_delta
                    if "commercial_artifact" in event.actions.state_delta:
                        commercial_generated = True

                if commercial_generated:
                    i += 1  # Move to COMMERCIAL_QA
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

    async def _generate_commercial_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate a multi-clip commercial deterministically using direct Veo SDK calls.

        Pipeline:
          1. Generate 2 reference images (character + product scene) via Gemini image gen
          2. Generate clip 1 with first-frame conditioning (reference image as first frame)
          3. Extract last frame from clip 1 for continuity
          4. Generate clip 2 with first-frame conditioning (last frame of clip 1)
          5. Concatenate clips with ffmpeg
          6. Trim to target duration
          7. Save commercial artifact via state_delta

        Each step emits a state_delta event for AE wave persistence.
        """
        state = ctx.session.state
        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "target consumers")
        selling_points = state.get("key_selling_points", "")
        duration = state.get("commercial_duration", 15)
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")
        bucket_name = bucket.replace("gs://", "")

        yield self._status_event(ctx, "Generating multi-clip commercial with deterministic AV studio...")

        veo_client = genai.Client(vertexai=True)
        img_client = genai.Client(vertexai=True)

        # --- Step 1: Get or generate reference images for first-frame conditioning ---
        ref_images = state.get("_commercial_ref_images", {})
        if not ref_images:
            yield self._status_event(ctx, "Step 1/6: Generating reference images for commercial scenes...")
            ref_images = await self._generate_reference_images(
                img_client, product, audience, selling_points, gcs_folder, bucket, bucket_name
            )
            if ref_images:
                save_ref_event = self._status_event(
                    ctx, f"Reference images generated: {len(ref_images)} scenes"
                )
                save_ref_event.actions.state_delta["_commercial_ref_images"] = ref_images
                yield save_ref_event
            else:
                yield self._status_event(ctx, "Reference image generation failed — using campaign images as fallback")
                # Fall back to campaign images
                img_keys = state.get("img_artifact_keys", {})
                if isinstance(img_keys, dict):
                    img_list = img_keys.get("img_artifact_keys", [])
                else:
                    img_list = img_keys if isinstance(img_keys, list) else []
                if img_list and gcs_folder and bucket:
                    first_img = img_list[0]
                    img_filename = first_img.get("artifact_key", "") if isinstance(first_img, dict) else str(first_img)
                    if img_filename:
                        ref_images = {"scene_1": f"{bucket}/{gcs_folder}/{img_filename}"}
        else:
            yield self._status_event(ctx, "Step 1/6: Reference images found in cache — skipping generation")

        # --- Step 2: Generate clips with Veo ---
        clips_cache = state.get("_commercial_clips", {})

        # Scene prompts for a 2-clip commercial
        scene_prompts = self._build_scene_prompts(product, audience, selling_points)

        # Generate clip 1
        clip_1_uri = clips_cache.get("clip_1")
        if not clip_1_uri:
            yield self._status_event(ctx, "Step 2/6: Generating clip 1 (opening scene)...")
            first_frame_uri = ref_images.get("scene_1", "")
            clip_1_uri = await self._generate_veo_clip(
                veo_client, scene_prompts[0], first_frame_uri, bucket
            )
            if clip_1_uri:
                clips_cache["clip_1"] = clip_1_uri
                clip_event = self._status_event(ctx, f"Clip 1 generated: {clip_1_uri}")
                clip_event.actions.state_delta["_commercial_clips"] = dict(clips_cache)
                yield clip_event
            else:
                yield self._status_event(ctx, "Clip 1 generation failed — trying single-shot fallback")
                async for event in self._generate_single_shot_fallback(ctx, veo_client, product, audience, selling_points, duration, bucket):
                    yield event
                return
        else:
            yield self._status_event(ctx, "Step 2/6: Clip 1 found in cache — skipping")

        # --- Step 3: Extract last frame from clip 1 for continuity ---
        last_frame_uri = clips_cache.get("clip_1_last_frame")
        if not last_frame_uri:
            yield self._status_event(ctx, "Step 3/6: Extracting last frame from clip 1 for continuity...")
            last_frame_uri = self._extract_last_frame(clip_1_uri, gcs_folder, bucket_name)
            if last_frame_uri:
                clips_cache["clip_1_last_frame"] = last_frame_uri
                frame_event = self._status_event(ctx, f"Last frame extracted: {last_frame_uri}")
                frame_event.actions.state_delta["_commercial_clips"] = dict(clips_cache)
                yield frame_event
            else:
                yield self._status_event(ctx, "Frame extraction failed — clip 2 will use reference image")
                last_frame_uri = ref_images.get("scene_2", ref_images.get("scene_1", ""))
        else:
            yield self._status_event(ctx, "Step 3/6: Last frame found in cache — skipping")

        # --- Step 4: Generate clip 2 with first-frame conditioning ---
        clip_2_uri = clips_cache.get("clip_2")
        if not clip_2_uri:
            yield self._status_event(ctx, "Step 4/6: Generating clip 2 (closing scene)...")
            clip_2_uri = await self._generate_veo_clip(
                veo_client, scene_prompts[1], last_frame_uri, bucket
            )
            if clip_2_uri:
                clips_cache["clip_2"] = clip_2_uri
                clip_event = self._status_event(ctx, f"Clip 2 generated: {clip_2_uri}")
                clip_event.actions.state_delta["_commercial_clips"] = dict(clips_cache)
                yield clip_event
            else:
                yield self._status_event(ctx, "Clip 2 failed — using clip 1 as the full commercial")
                # Use clip 1 as the full commercial
                clip_uris = [clip_1_uri]
                async for event in self._finalize_commercial(ctx, clip_uris, duration, product, audience, gcs_folder, bucket_name):
                    yield event
                return
        else:
            yield self._status_event(ctx, "Step 4/6: Clip 2 found in cache — skipping")

        # --- Step 5 & 6: Concatenate and trim ---
        clip_uris = [clip_1_uri, clip_2_uri]
        async for event in self._finalize_commercial(ctx, clip_uris, duration, product, audience, gcs_folder, bucket_name):
            yield event

    async def _generate_reference_images(
        self, img_client, product: str, audience: str, selling_points: str,
        gcs_folder: str, bucket: str, bucket_name: str,
    ) -> dict:
        """Generate reference images for commercial scenes."""
        ref_images = {}
        scene_descriptions = [
            (
                "scene_1",
                f"A {audience.split()[0] if audience else 'young'} person in a bright, "
                f"modern laundry room discovering {product}. Natural morning light through "
                f"window, clean minimalist aesthetic. The person looks delighted while holding "
                f"the product. Lifestyle photography, warm tones, high quality."
            ),
            (
                "scene_2",
                f"Close-up of {product} with fresh hibiscus flowers arranged around it. "
                f"Soft bokeh background, product hero shot. Natural daylight, premium "
                f"feel. {selling_points[:100]}. Studio quality product photography."
            ),
        ]

        for scene_name, prompt in scene_descriptions:
            try:
                response = None
                for attempt in range(3):
                    try:
                        response = img_client.models.generate_content(
                            model=config.subject_image_gen_model,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_modalities=["IMAGE"],
                            ),
                        )
                        break
                    except Exception as e:
                        if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < 2:
                            time.sleep(15 * (attempt + 1))
                        else:
                            raise

                if not response or not response.candidates:
                    continue

                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                        filename = f"commercial_ref_{scene_name}.png"
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                            tmp.write(part.inline_data.data)
                            tmp_path = tmp.name
                        try:
                            dest_blob = f"{gcs_folder}/av_studio/refs/{filename}"
                            upload_blob_to_gcs(
                                source_file_name=tmp_path,
                                destination_blob_name=dest_blob,
                            )
                            gcs_uri = f"gs://{bucket_name}/{dest_blob}"
                            ref_images[scene_name] = gcs_uri
                            logger.info(f"[DetAV] Reference image {scene_name}: {gcs_uri}")
                        finally:
                            os.unlink(tmp_path)
                        break

            except Exception as e:
                logger.warning(f"[DetAV] Reference image {scene_name} failed: {e}")

        return ref_images

    async def _generate_veo_clip(
        self, veo_client, prompt: str, first_frame_gcs_uri: str, bucket: str,
    ) -> str | None:
        """Generate a single Veo clip, optionally with first-frame conditioning."""
        try:
            gen_config = GenerateVideosConfig(
                aspect_ratio="16:9",
                number_of_videos=1,
                output_gcs_uri=bucket,
            )

            if first_frame_gcs_uri:
                first_frame_image = types.Image(
                    gcs_uri=first_frame_gcs_uri, mime_type="image/png"
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

            start_time = time.time()
            while not operation.done:
                if time.time() - start_time > MAX_VEO_POLL_SECONDS:
                    logger.warning("[DetAV] Veo clip timed out")
                    return None
                await asyncio.sleep(15)
                operation = veo_client.operations.get(operation)

            if operation.error:
                logger.warning(f"[DetAV] Veo error: {operation.error}")
                # Retry without first-frame if it failed with one
                if first_frame_gcs_uri:
                    logger.info("[DetAV] Retrying without first-frame conditioning...")
                    operation = veo_client.models.generate_videos(
                        model=config.video_gen_model,
                        prompt=prompt,
                        config=gen_config,
                    )
                    start_time = time.time()
                    while not operation.done:
                        if time.time() - start_time > MAX_VEO_POLL_SECONDS:
                            return None
                        await asyncio.sleep(15)
                        operation = veo_client.operations.get(operation)
                    if operation.error:
                        return None

            if operation.result and operation.result.generated_videos:
                for video in operation.result.generated_videos:
                    if video.video and video.video.uri:
                        return video.video.uri

            return None

        except Exception as e:
            logger.warning(f"[DetAV] Veo clip exception: {e}")
            return None

    def _extract_last_frame(
        self, clip_gcs_uri: str, gcs_folder: str, bucket_name: str,
    ) -> str | None:
        """Extract the last frame from a clip for visual continuity."""
        try:
            source_blob = clip_gcs_uri.replace(f"gs://{bucket_name}/", "")

            with tempfile.TemporaryDirectory() as temp_dir:
                local_video = os.path.join(temp_dir, "clip.mp4")
                download_image_from_gcs(
                    source_blob_name=source_blob,
                    destination_file_name=local_video,
                    gcs_bucket=bucket_name,
                )

                cap = cv2.VideoCapture(local_video)
                if not cap.isOpened():
                    logger.warning("[DetAV] Could not open clip for frame extraction")
                    return None

                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_frames - 1))
                ret, frame = cap.read()
                cap.release()

                if not ret:
                    return None

                frame_path = os.path.join(temp_dir, "last_frame.png")
                cv2.imwrite(frame_path, frame)

                dest_blob = f"{gcs_folder}/av_studio/frames/clip1_last_frame.png"
                upload_blob_to_gcs(
                    source_file_name=frame_path,
                    destination_blob_name=dest_blob,
                )
                gcs_uri = f"gs://{bucket_name}/{dest_blob}"
                logger.info(f"[DetAV] Extracted last frame: {gcs_uri}")
                return gcs_uri

        except Exception as e:
            logger.warning(f"[DetAV] Frame extraction failed: {e}")
            return None

    async def _finalize_commercial(
        self, ctx: InvocationContext, clip_uris: list[str],
        duration: int, product: str, audience: str,
        gcs_folder: str, bucket_name: str,
    ) -> AsyncGenerator[Event, None]:
        """Concatenate clips, trim to target duration, and save commercial artifact."""
        state = ctx.session.state

        if len(clip_uris) == 1:
            # Single clip — just trim
            yield self._status_event(ctx, "Step 5/6: Single clip — skipping concatenation...")
            raw_uri = clip_uris[0]
        else:
            # Concatenate clips
            yield self._status_event(ctx, f"Step 5/6: Concatenating {len(clip_uris)} clips with ffmpeg...")
            raw_uri = self._concatenate_clips(clip_uris, gcs_folder, bucket_name)
            if not raw_uri:
                yield self._status_event(ctx, "Concatenation failed — using clip 1 as commercial")
                raw_uri = clip_uris[0]

        # Trim to target duration
        yield self._status_event(ctx, f"Step 6/6: Trimming to {duration}s...")
        final_uri = self._trim_video(raw_uri, duration, gcs_folder, bucket_name)
        if not final_uri:
            final_uri = raw_uri  # Use untrimmed if trim fails

        # Save commercial artifact
        commercial_data = {
            "artifact_key": f"commercial_{duration}s.mp4",
            "gcs_uri": final_uri,
            "metadata": {
                "title": f"{duration}s commercial for {product}",
                "scene_descriptions": [
                    f"Opening: Character discovers {product}",
                    f"Closing: Product hero shot with {product}",
                ],
                "total_clips": len(clip_uris),
                "duration_seconds": duration,
                "narrative_arc": f"Discovery → delight → product reveal for {product}",
                "target_audience_appeal": f"Designed for {audience}",
                "deterministic_av_studio": True,
            },
        }
        event = self._status_event(ctx, f"Commercial generated: {final_uri}")
        event.actions.state_delta["commercial_artifact"] = commercial_data
        yield event
        logger.info(f"[DetAV] Commercial saved: {final_uri}")

    def _concatenate_clips(
        self, clip_uris: list[str], gcs_folder: str, bucket_name: str,
    ) -> str | None:
        """Concatenate clips using ffmpeg."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                local_paths = []
                for idx, uri in enumerate(clip_uris):
                    source_blob = uri.replace(f"gs://{bucket_name}/", "")
                    local_path = os.path.join(temp_dir, f"clip_{idx}.mp4")
                    download_image_from_gcs(
                        source_blob_name=source_blob,
                        destination_file_name=local_path,
                        gcs_bucket=bucket_name,
                    )
                    local_paths.append(local_path)
                    logger.info(f"[DetAV] Downloaded clip {idx}: {os.path.getsize(local_path)} bytes")

                # Create concat file list
                concat_list = os.path.join(temp_dir, "concat.txt")
                with open(concat_list, "w") as f:
                    for p in local_paths:
                        f.write(f"file '{p}'\n")

                output_name = f"commercial_raw_{uuid.uuid4().hex[:8]}.mp4"
                output_path = os.path.join(temp_dir, output_name)

                subprocess.run(
                    [FFMPEG_BIN, "-f", "concat", "-safe", "0",
                     "-i", concat_list, "-c", "copy", output_path],
                    check=True, capture_output=True, text=True,
                )

                # Upload concatenated video
                dest_blob = f"{gcs_folder}/av_studio/{output_name}"
                upload_blob_to_gcs(
                    source_file_name=output_path,
                    destination_blob_name=dest_blob,
                )
                gcs_uri = f"gs://{bucket_name}/{dest_blob}"
                logger.info(f"[DetAV] Concatenated {len(clip_uris)} clips: {gcs_uri}")
                return gcs_uri

        except Exception as e:
            logger.warning(f"[DetAV] Concatenation failed: {e}")
            return None

    def _trim_video(
        self, video_uri: str, target_seconds: int,
        gcs_folder: str, bucket_name: str,
    ) -> str | None:
        """Trim video to target duration with ffmpeg."""
        try:
            source_blob = video_uri.replace(f"gs://{bucket_name}/", "")

            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = os.path.join(temp_dir, "input.mp4")
                download_image_from_gcs(
                    source_blob_name=source_blob,
                    destination_file_name=input_path,
                    gcs_bucket=bucket_name,
                )

                output_name = f"commercial_{target_seconds}s_{uuid.uuid4().hex[:8]}.mp4"
                output_path = os.path.join(temp_dir, output_name)

                subprocess.run(
                    [FFMPEG_BIN, "-i", input_path, "-t", str(target_seconds),
                     "-c", "copy", output_path],
                    check=True, capture_output=True, text=True,
                )

                dest_blob = f"{gcs_folder}/av_studio/{output_name}"
                upload_blob_to_gcs(
                    source_file_name=output_path,
                    destination_blob_name=dest_blob,
                )
                gcs_uri = f"gs://{bucket_name}/{dest_blob}"
                logger.info(f"[DetAV] Trimmed to {target_seconds}s: {gcs_uri}")
                return gcs_uri

        except Exception as e:
            logger.warning(f"[DetAV] Trim failed: {e}")
            return None

    def _build_scene_prompts(self, product: str, audience: str, selling_points: str) -> list[str]:
        """Build detailed Veo prompts for each scene in the commercial."""
        return [
            # Clip 1: Opening — character discovery
            (
                f"<SUBJECT> A young eco-conscious person in a modern bright laundry room. "
                f"<ACTION> They pick up {product} from a shelf, look at it curiously, then smell "
                f"the cap and smile with genuine delight. Their expression goes from curiosity to "
                f"pleasant surprise. "
                f"<SCENE_AND_CONTEXT> Clean, minimalist laundry room with natural morning light "
                f"streaming through a window. Fresh plants visible. Eco-friendly aesthetic. "
                f"<CAMERA_ANGLE> Medium shot, slightly low angle to make the product feel premium. "
                f"<CAMERA_MOVEMENTS> Slow dolly-in from medium to medium close-up. "
                f"<VISUAL_STYLE_AND_AESTHETICS> Warm golden hour tones, shallow depth of field, "
                f"cinematic 24fps look. Premium lifestyle commercial quality. "
                f"SUPPRESS SUBTITLES. NO TEXT ON SCREEN."
            ),
            # Clip 2: Closing — product hero + satisfaction
            (
                f"<SUBJECT> {product} bottle in the foreground with fresh hibiscus flowers. "
                f"The same person from the previous scene is in soft focus background, folding "
                f"fresh laundry and looking satisfied. "
                f"<ACTION> Camera focuses on the product, a gentle breeze moves the hibiscus "
                f"petals. The person in background brings fabric to their nose and smiles. "
                f"<SCENE_AND_CONTEXT> Same laundry room. Stack of perfectly folded colorful "
                f"clothes nearby. Clean, fresh atmosphere. {selling_points[:80]}. "
                f"<CAMERA_ANGLE> Low angle product hero shot with bokeh background. "
                f"<CAMERA_MOVEMENTS> Very slow push-in on the product. "
                f"<VISUAL_STYLE_AND_AESTHETICS> Warm tones, premium product photography meets "
                f"lifestyle commercial. Soft lens flare from window light. "
                f"SUPPRESS SUBTITLES. NO TEXT ON SCREEN."
            ),
        ]

    async def _generate_single_shot_fallback(
        self, ctx: InvocationContext, veo_client, product: str,
        audience: str, selling_points: str, duration: int, bucket: str,
    ) -> AsyncGenerator[Event, None]:
        """Last-resort: single Veo clip without first-frame conditioning."""
        yield self._status_event(ctx, "Generating single-shot fallback commercial...")

        prompt = (
            f"A cinematic {duration}-second commercial for {product}. "
            f"Targeting {audience}. Key features: {selling_points}. "
            f"Smooth camera movement, warm natural lighting, lifestyle setting. "
            f"Product prominently featured. No text or logos in the video."
        )

        clip_uri = await self._generate_veo_clip(veo_client, prompt, "", bucket)
        if clip_uri:
            commercial_data = {
                "artifact_key": f"commercial_{duration}s.mp4",
                "gcs_uri": clip_uri,
                "metadata": {
                    "title": f"{duration}s commercial for {product}",
                    "scene_descriptions": [f"Single-shot lifestyle commercial for {product}"],
                    "total_clips": 1,
                    "duration_seconds": duration,
                    "narrative_arc": f"Product showcase for {product}",
                    "target_audience_appeal": f"Designed for {audience}",
                    "single_shot_fallback": True,
                },
            }
            event = self._status_event(ctx, f"Fallback commercial generated: {clip_uri}")
            event.actions.state_delta["commercial_artifact"] = commercial_data
            yield event
        else:
            yield self._status_event(ctx, "All commercial generation attempts failed")

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
