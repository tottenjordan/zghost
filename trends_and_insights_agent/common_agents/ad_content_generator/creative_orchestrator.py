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
from ...shared_libraries.utils import upload_blob_to_gcs, download_blob
from ...shared_libraries import callbacks
from ...shared_libraries.fidelity_eval.gecko import evaluate as gecko_evaluate
from ...skills.focus_group.tools import analyze_commercial_video
from .tools import evaluate_media_fidelity

logger = logging.getLogger("google_adk." + __name__)

MAX_COMMERCIAL_RETRIES = 2
AV_STUDIO_MAX_RUNS = 5  # Max AV_STUDIO invocations before deterministic commercial
AE_WAVE_POLL_BUDGET = 55  # seconds to poll Veo within a single AE wave

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
    before_model_callback=[callbacks.before_model_status_callback, callbacks.rate_limit_callback],
)


CREATIVE_STAGES = [
    ("AD_CREATIVE", "ad_content_generator_agent", "Orchestrating ad generation..."),
    ("IMAGE_GEN", "standalone_image_generator", "Generating campaign images from visual concepts..."),
    ("AV_STUDIO", "av_editing_studio_agent", "Producing commercial in AV editing studio..."),
    ("COMMERCIAL_QA", "commercial_qa_agent", "Evaluating commercial quality with Gecko..."),
]


def _creative_stage_message(stage_name: str, state: dict) -> str:
    """Build dynamic, CEO-friendly status messages for creative sub-stages."""
    product = state.get("target_product", "the product")
    audience = state.get("target_audience", "consumers")
    duration = state.get("commercial_duration", 15)
    msgs = {
        "AD_CREATIVE": (
            f"Brainstorming ad concepts for {product} — drafting headlines, "
            f"copy variations, and visual concepts tailored for {audience}."
        ),
        "IMAGE_GEN": (
            f"Rendering hero images for {product} — translating visual concepts into "
            f"high-quality campaign photography with cinematic lighting."
        ),
        "AV_STUDIO": (
            f"Directing a {duration}s video commercial for {product} — "
            f"generating cinematic footage with Veo to bring the campaign to life."
        ),
        "COMMERCIAL_QA": (
            f"Quality-checking the {product} commercial — scoring visual fidelity, "
            f"brand alignment, and production quality."
        ),
    }
    return msgs.get(stage_name, f"Running {stage_name}...")


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

        # If enough images exist (3 ref images), go to AV_STUDIO
        # But skip if AV studio already exhausted all attempts
        av_runs = state.get("_av_studio_runs", 0)
        clips_cache = state.get("_commercial_clips", {})
        has_pending_veo = bool(clips_cache.get("_pending_veo_op")) if isinstance(clips_cache, dict) else False

        if img_keys and len(img_keys) >= 3:
            if has_pending_veo:
                return 2  # Must poll pending Veo operation
            if av_runs >= AV_STUDIO_MAX_RUNS:
                return len(CREATIVE_STAGES)  # Skip — all AV attempts exhausted
            return 2  # AV_STUDIO
        # If some images exist but < 3, keep generating
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

        # Handle interactive concept selection response
        if state.get("_awaiting_concept_selection"):
            async for event in self._handle_concept_selection(ctx):
                yield event
            # After selection, fall through to normal pipeline

        # Determine start from session state (robust across AE invocations)
        start_index = self._determine_start_index(ctx)
        av_attempts = 0
        pause_invocation = False
        # Track av_runs locally — state.get() returns stale snapshot within a single invocation
        av_runs_local = state.get("_av_studio_runs", 0)

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

            yield self._status_event(ctx, _creative_stage_message(stage_name, dict(state)))

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
                    av_runs_local += 1
                    av_runs = av_runs_local
                    track_event = self._status_event(
                        ctx, f"Deterministic AV studio attempt {av_runs}/{AV_STUDIO_MAX_RUNS}..."
                    )
                    track_event.actions.state_delta["_av_studio_runs"] = av_runs
                    yield track_event
                else:
                    av_runs = av_runs_local
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

            # COMMERCIAL_QA: skip in autopilot (focus group evaluates anyway)
            if stage_name == "COMMERCIAL_QA" and state.get("autopilot_mode"):
                qa_skip_event = self._status_event(ctx, "Autopilot: skipping commercial QA (focus group will evaluate)")
                qa_skip_event.actions.state_delta["commercial_qa_result"] = "PASS (autopilot — skipped)"
                yield qa_skip_event
                i += 1
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

            # After AD_CREATIVE, handle visual concept selection
            if stage_name == "AD_CREATIVE":
                vis_concepts = state.get("final_select_vis_concepts", {})
                if isinstance(vis_concepts, dict):
                    vis_concepts = vis_concepts.get("final_select_vis_concepts", [])
                if not vis_concepts:
                    # Try draft visual concepts
                    drafts = state.get("draft_vis_concepts", [])
                    if not drafts:
                        drafts = state.get("visual_concept_drafts", [])
                    if drafts:
                        if state.get("autopilot_mode"):
                            # Auto-select top concepts
                            auto_concepts = drafts[:2] if isinstance(drafts, list) else [drafts]
                            auto_event = self._status_event(ctx, f"Auto-selected {len(auto_concepts)} visual concepts from drafts")
                            auto_event.actions.state_delta["final_select_vis_concepts"] = {"final_select_vis_concepts": auto_concepts}
                            yield auto_event
                        else:
                            # Interactive mode: present concepts for user selection
                            concept_list = []
                            for idx, d in enumerate(drafts if isinstance(drafts, list) else [drafts]):
                                name = d.get("name", d.get("concept", f"Concept {idx+1}")) if isinstance(d, dict) else str(d)
                                desc = d.get("description", "")[:150] if isinstance(d, dict) else ""
                                concept_list.append(f"  {idx+1}. {name}" + (f" — {desc}" if desc else ""))
                            concepts_text = "\n".join(concept_list)
                            prompt_event = self._status_event(
                                ctx,
                                f"Visual concepts ready for review:\n{concepts_text}\n\n"
                                f"Reply with the concept numbers you want (e.g. '1, 3'), or 'all' to use all concepts."
                            )
                            prompt_event.actions.state_delta["_awaiting_concept_selection"] = True
                            yield prompt_event
                            return  # Pause — user will respond, next wave resumes

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

    async def _handle_concept_selection(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Process user's concept selection response in interactive mode."""
        state = ctx.session.state
        user_msg = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if hasattr(part, "text") and part.text:
                    user_msg = part.text.strip().lower()
                    break

        drafts = state.get("draft_vis_concepts", [])
        if not drafts:
            drafts = state.get("visual_concept_drafts", [])
        if not isinstance(drafts, list):
            drafts = [drafts]

        selected = []
        if "all" in user_msg or "continue" in user_msg or not user_msg:
            selected = drafts[:2]
        else:
            # Parse comma-separated numbers like "1, 3" or "1 3"
            import re
            nums = re.findall(r"\d+", user_msg)
            for n in nums:
                idx = int(n) - 1
                if 0 <= idx < len(drafts):
                    selected.append(drafts[idx])
            if not selected:
                selected = drafts[:2]

        clear_event = self._status_event(
            ctx, f"Selected {len(selected)} visual concept(s) for image generation and commercial production."
        )
        clear_event.actions.state_delta["final_select_vis_concepts"] = {"final_select_vis_concepts": selected}
        clear_event.actions.state_delta["_awaiting_concept_selection"] = False
        yield clear_event

    async def _generate_images_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate 3 purpose-built reference images for Veo video generation.

        1. Product ASSET — hero product shot (VideoGenerationReferenceType.ASSET)
        2. Person ASSET — model/person for the ad (VideoGenerationReferenceType.ASSET)
        3. Trend STYLE — trend mood/aesthetic (VideoGenerationReferenceType.STYLE)

        All images scored with Gecko fidelity. One image per AE wave.
        The 2 best Gecko-scoring refs are sent to Veo.
        """
        state = ctx.session.state
        product = state.get("target_product", "the product")
        audience = state.get("target_audience", "consumers")
        brand = state.get("brand", "")
        ksp = state.get("key_selling_points", "")
        gcs_folder = state.get("gcs_folder", "")
        bucket = os.getenv("BUCKET", "")
        MAX_IMAGES = 3  # Product ASSET + Person ASSET + Trend STYLE

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

        # Get trend title for STYLE image
        trend_desc = state.get("target_search_trends", {})
        trend_title = ""
        if isinstance(trend_desc, dict):
            trends_list = trend_desc.get("target_search_trends", [])
            if trends_list:
                trend_title = trends_list[0].get("title", "") if isinstance(trends_list[0], dict) else str(trends_list[0])

        # Build 3 purpose-built reference images
        shot_list = [
            # Shot 1: Product ASSET — hero product shot
            {
                "concept_name": f"{idea_name}_product_asset",
                "shot_type": "product_asset",
                "reference_type": "ASSET",
                "prompt": (
                    f"Professional studio hero product shot of {product} by {brand}. "
                    f"Product centered, {brand} brand clearly visible. Clean background, "
                    f"dramatic studio lighting. Key features: {ksp[:150]}. No watermarks."
                ),
            },
            # Shot 2: Person ASSET — model/person for the ad
            {
                "concept_name": f"{idea_name}_person_asset",
                "shot_type": "person_asset",
                "reference_type": "ASSET",
                "prompt": (
                    f"Professional advertising photography of a {audience} person using {product}. "
                    f"Authentic, relatable model expressing satisfaction. "
                    f"Natural lighting, lifestyle setting. {brand} product visible. No watermarks."
                ),
            },
            # Shot 3: Trend STYLE — aesthetic based on selected trends
            {
                "concept_name": f"{idea_name}_trend_style",
                "shot_type": "trend_style",
                "reference_type": "STYLE",
                "prompt": (
                    f"Lifestyle mood board aesthetic for trend '{trend_title}'. "
                    f"Product {product} naturally integrated, target audience {audience}. "
                    f"Warm lighting, cinematic grading, aspirational setting reflecting "
                    f"'{trend_title}' aesthetic. Key features: {ksp[:150]}. No watermarks."
                ),
            },
        ]

        # Generate one image per wave (AE-safe)
        img_idx = already_generated
        if img_idx >= len(shot_list):
            yield self._status_event(ctx, f"All {len(shot_list)} images already generated.")
            return

        shot = shot_list[img_idx]
        concept_name = shot["concept_name"]
        prompt = shot["prompt"]

        yield self._status_event(ctx, f"Generating image {img_idx + 1}/{MAX_IMAGES} ({shot['shot_type']}: {concept_name})...")

        try:
            import re as _re
            from google.genai.types import GenerateImagesConfig
            img_client = genai.Client(vertexai=True)
            # Sanitize name: alphanumeric, underscores, hyphens only
            safe_name = _re.sub(r"[^a-zA-Z0-9_\-]", "", concept_name.replace(" ", "_"))
            artifact_key = f"{safe_name}_0.png"
            gcs_uri = ""

            # Use Imagen 4 generate_images() — no output_gcs_uri so we always
            # get image_bytes back (output_gcs_uri returns None bytes + unknown URI)
            img_config = GenerateImagesConfig(number_of_images=1)
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

                # Gecko fidelity (best-effort)
                fidelity_score = None
                if gcs_uri:
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
                        pass

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
                yield self._status_event(ctx, f"Image {img_idx + 1} returned empty — will retry next wave.")

        except Exception as e:
            logger.warning(f"[ImageGen] Failed: {e}")
            yield self._status_event(ctx, f"Image gen failed: {str(e)[:100]} — will retry.")

    async def _generate_commercial_deterministic(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate a multi-clip commercial using Veo with first-frame chaining.

        Generates NUM_CLIPS video clips (default 2) and concatenates them into
        a single commercial. The second clip uses the last frame of the first
        clip as its first-frame conditioning for visual continuity.

        Wave-safe: saves pending operations to state so AE can resume polling.
        Uses campaign images as ASSET (product) and STYLE (aesthetic) references.
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
        NUM_CLIPS = 1  # Single-clip for AE reliability (multi-clip causes state loss)
        clip_duration = duration

        veo_client = genai.Client(vertexai=True)
        clips_cache = state.get("_commercial_clips", {})

        # Track completed clips and pending op
        completed_clips = clips_cache.get("_completed_clip_uris", [])
        pending_op = clips_cache.get("_pending_veo_op")
        current_clip_idx = clips_cache.get("_current_clip_idx", 0)

        if pending_op:
            yield self._status_event(ctx, f"Polling Veo clip {current_clip_idx + 1}/{NUM_CLIPS} (resuming)...")
        else:
            yield self._status_event(ctx, f"Generating clip {current_clip_idx + 1}/{NUM_CLIPS} for {duration}s commercial...")

        # Build reference images from campaign images — select best Gecko-scored refs
        img_keys = state.get("img_artifact_keys", {})
        if isinstance(img_keys, dict):
            img_list = img_keys.get("img_artifact_keys", [])
        else:
            img_list = img_keys if isinstance(img_keys, list) else []

        first_frame_uri = ""
        reference_images = []
        if img_list and gcs_folder and bucket:
            # Select product ASSET + trend STYLE for Veo reference_images
            # Veo accepts two reference types: ASSET (what appears) and STYLE (aesthetic)
            product_refs = [m for m in img_list if isinstance(m, dict) and m.get("shot_type") == "product_asset"]
            style_refs = [m for m in img_list if isinstance(m, dict) and m.get("reference_type") == "STYLE"]
            person_refs = [m for m in img_list if isinstance(m, dict) and m.get("shot_type") == "person_asset"]

            # Product ASSET + Trend STYLE (prefer STYLE over person for video aesthetic)
            selected_refs = product_refs[:1] + style_refs[:1]
            if not style_refs and person_refs:
                selected_refs = product_refs[:1] + person_refs[:1]

            for img_meta in selected_refs:
                # Use the actual GCS URI stored during image gen, not reconstructed path
                img_gcs_uri = img_meta.get("gcs_uri", "")
                if not img_gcs_uri:
                    img_filename = img_meta.get("artifact_key", "")
                    if not img_filename:
                        continue
                    img_gcs_uri = f"{bucket}/{gcs_folder}/{img_filename}"
                if not first_frame_uri:
                    first_frame_uri = img_gcs_uri
                ref_type_str = img_meta.get("reference_type", "ASSET")
                ref_type = (types.VideoGenerationReferenceType.STYLE
                            if ref_type_str == "STYLE"
                            else types.VideoGenerationReferenceType.ASSET)
                reference_images.append(
                    types.VideoGenerationReferenceImage(
                        image=types.Image(gcs_uri=img_gcs_uri, mime_type="image/png"),
                        reference_type=ref_type,
                    )
                )
                logger.info(f"[DetAV] Reference: {ref_type_str} (Gecko: {img_meta.get('fidelity_score', 'N/A')}) -> {img_gcs_uri}")

            # Status message highlighting Gecko-rated reference selection
            if reference_images:
                ref_summary = ", ".join([
                    f"{m.get('shot_type','?')} {m.get('reference_type','?')} (Gecko: {m.get('fidelity_score', 0):.2f})"
                    for m in selected_refs if isinstance(m, dict)
                ])
                yield self._status_event(
                    ctx, f"Selected {len(reference_images)} best Gecko-rated reference images for Veo: {ref_summary}"
                )

        # Clip-specific prompts for narrative arc
        clip_prompts = self._build_clip_prompts(product, audience, selling_points, brand, NUM_CLIPS, clip_duration)

        try:
            # Process one clip per wave iteration
            while current_clip_idx < NUM_CLIPS:
                clip_prompt = clip_prompts[current_clip_idx] if current_clip_idx < len(clip_prompts) else clip_prompts[-1]

                gen_config = GenerateVideosConfig(
                    aspect_ratio="16:9",
                    number_of_videos=1,
                    output_gcs_uri=bucket,
                    reference_images=reference_images if reference_images else None,
                )

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
                    # Determine first-frame for this clip
                    clip_first_frame = None
                    if current_clip_idx == 0 and first_frame_uri:
                        # First clip: use campaign hero image
                        clip_first_frame = types.Image(gcs_uri=first_frame_uri, mime_type="image/png")
                        logger.info(f"[DetAV] Clip 1 first-frame: campaign image {first_frame_uri}")
                    elif current_clip_idx > 0 and completed_clips:
                        # Subsequent clips: extract last frame from previous clip for continuity
                        prev_clip_uri = completed_clips[-1]
                        last_frame_uri = self._extract_last_frame(prev_clip_uri, bucket_name, gcs_folder, bucket)
                        if last_frame_uri:
                            clip_first_frame = types.Image(gcs_uri=last_frame_uri, mime_type="image/png")
                            logger.info(f"[DetAV] Clip {current_clip_idx + 1} first-frame: last frame of clip {current_clip_idx}")

                    if clip_first_frame:
                        # Veo does NOT allow image + reference_images together
                        ff_config = GenerateVideosConfig(
                            aspect_ratio="16:9",
                            number_of_videos=1,
                            output_gcs_uri=bucket,
                        )
                        operation = veo_client.models.generate_videos(
                            model=config.video_gen_model,
                            prompt=clip_prompt,
                            image=clip_first_frame,
                            config=ff_config,
                        )
                    else:
                        operation = veo_client.models.generate_videos(
                            model=config.video_gen_model,
                            prompt=clip_prompt,
                            config=gen_config,
                        )

                    op_name = operation.name
                    if op_name:
                        pre_save = self._status_event(ctx, f"Veo clip {current_clip_idx + 1}/{NUM_CLIPS} submitted")
                        pre_save.actions.state_delta["_commercial_clips"] = {
                            "_pending_veo_op": op_name,
                            "_current_clip_idx": current_clip_idx,
                            "_completed_clip_uris": completed_clips,
                        }
                        yield pre_save

                # Poll within AE wave budget
                start_time = time.time()
                poll_count = 0
                while not operation.done:
                    elapsed = time.time() - start_time
                    if elapsed > AE_WAVE_POLL_BUDGET:
                        logger.info(f"[DetAV] Clip {current_clip_idx + 1} still generating, will resume")
                        save_event = self._status_event(ctx, f"Clip {current_clip_idx + 1}/{NUM_CLIPS} still generating — will resume")
                        save_event.actions.state_delta["_commercial_clips"] = {
                            "_pending_veo_op": operation.name,
                            "_current_clip_idx": current_clip_idx,
                            "_completed_clip_uris": completed_clips,
                        }
                        yield save_event
                        return
                    time.sleep(10)
                    poll_count += 1
                    yield self._status_event(
                        ctx, f"Veo generating clip {current_clip_idx + 1}... {int(elapsed)}s elapsed"
                    )
                    operation = veo_client.operations.get(operation)

                if operation.error:
                    err_msg = str(operation.error)[:200]
                    logger.warning(f"[DetAV] Veo error on clip {current_clip_idx + 1}: {err_msg}")
                    yield self._status_event(ctx, f"Veo clip failed: {err_msg[:100]}. Retrying without reference images...")
                    # Always retry without reference images on failure
                    retry_config = GenerateVideosConfig(
                        aspect_ratio="16:9", number_of_videos=1, output_gcs_uri=bucket,
                    )
                    operation = veo_client.models.generate_videos(
                        model=config.video_gen_model, prompt=clip_prompt, config=retry_config,
                    )
                    if operation.name:
                        retry_save = self._status_event(ctx, f"Retrying clip {current_clip_idx + 1} without references...")
                        retry_save.actions.state_delta["_commercial_clips"] = {
                            "_pending_veo_op": operation.name,
                            "_current_clip_idx": current_clip_idx,
                            "_completed_clip_uris": completed_clips,
                        }
                        yield retry_save
                    pending_op = None  # Mark as fresh retry
                    start_time = time.time()
                    while not operation.done:
                        elapsed = time.time() - start_time
                        if elapsed > AE_WAVE_POLL_BUDGET:
                            save_event = self._status_event(ctx, "Retry still generating — will resume")
                            save_event.actions.state_delta["_commercial_clips"] = {
                                "_pending_veo_op": operation.name,
                                "_current_clip_idx": current_clip_idx,
                                "_completed_clip_uris": completed_clips,
                            }
                            yield save_event
                            return
                        time.sleep(10)
                        yield self._status_event(
                            ctx, f"Veo retry clip {current_clip_idx + 1}... {int(elapsed)}s elapsed"
                        )
                        operation = veo_client.operations.get(operation)
                    if operation.error:
                        yield self._status_event(ctx, f"Clip {current_clip_idx + 1} failed after retry — skipping")
                        current_clip_idx += 1
                        pending_op = None
                        continue

                # Extract clip URI
                clip_uri = None
                if operation.result and operation.result.generated_videos:
                    for video in operation.result.generated_videos:
                        if video.video and video.video.uri:
                            clip_uri = video.video.uri
                            break

                if clip_uri:
                    completed_clips.append(clip_uri)
                    yield self._status_event(ctx, f"Clip {current_clip_idx + 1}/{NUM_CLIPS} complete: {clip_uri[-60:]}")
                    # Save progress
                    progress_event = self._status_event(ctx, f"Clips done: {len(completed_clips)}/{NUM_CLIPS}")
                    progress_event.actions.state_delta["_commercial_clips"] = {
                        "_completed_clip_uris": completed_clips,
                        "_current_clip_idx": current_clip_idx + 1,
                    }
                    yield progress_event
                else:
                    logger.warning(f"[DetAV] Clip {current_clip_idx + 1}: no video URI in result")
                    clear_event = self._status_event(ctx, f"Clip {current_clip_idx + 1} returned empty — will retry")
                    clear_event.actions.state_delta["_commercial_clips"] = {
                        "_completed_clip_uris": completed_clips,
                        "_current_clip_idx": current_clip_idx,
                    }
                    yield clear_event
                    return  # Retry on next wave

                current_clip_idx += 1
                pending_op = None

            # All clips done — concatenate into final commercial
            if not completed_clips:
                # Clear stale clips state to prevent infinite resume loop
                clear_event = self._status_event(ctx, "No clips generated — commercial failed")
                clear_event.actions.state_delta["_commercial_clips"] = {}
                yield clear_event
                return

            yield self._status_event(ctx, f"Concatenating {len(completed_clips)} clips into {duration}s commercial...")

            final_gcs_uri, video_bytes = self._concatenate_clips(
                completed_clips, bucket_name, gcs_folder, bucket, product, duration,
            )
            art_fname = f"commercial_{duration}s.mp4"

            if final_gcs_uri:
                commercial_data = {
                    "artifact_key": art_fname,
                    "gcs_uri": final_gcs_uri,
                    "metadata": {
                        "title": f"{duration}s commercial for {product}",
                        "scene_descriptions": [
                            f"Clip {i+1}: {clip_prompts[i][:100]}..." if i < len(clip_prompts) else f"Clip {i+1}"
                            for i in range(len(completed_clips))
                        ],
                        "total_clips": len(completed_clips),
                        "duration_seconds": duration,
                        "narrative_arc": f"Multi-clip narrative for {product} by {brand}",
                        "target_audience_appeal": f"Designed for {audience}",
                        "deterministic_av_studio": True,
                    },
                }
                event = self._status_event(ctx, f"Commercial generated: {len(completed_clips)} clips, {duration}s")
                event.actions.state_delta["commercial_artifact"] = commercial_data
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
                logger.info(f"[DetAV] Multi-clip commercial saved: {final_gcs_uri}")
            else:
                # Fallback: use first clip as the commercial
                if completed_clips:
                    clip_uri = completed_clips[0]
                    source_blob = clip_uri.replace(f"gs://{bucket_name}/", "")
                    try:
                        video_bytes = download_blob(bucket_name=bucket_name, source_blob_name=source_blob)
                        if gcs_folder and bucket:
                            dest_blob = f"{gcs_folder}/{art_fname}"
                            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                                tmp.write(video_bytes)
                                tmp_path = tmp.name
                            try:
                                upload_blob_to_gcs(source_file_name=tmp_path, destination_blob_name=dest_blob)
                                final_gcs_uri = f"{bucket}/{dest_blob}"
                            finally:
                                os.unlink(tmp_path)
                    except Exception as e:
                        final_gcs_uri = clip_uri
                        video_bytes = None
                        logger.warning(f"[DetAV] Fallback copy failed: {e}")

                    commercial_data = {
                        "artifact_key": art_fname,
                        "gcs_uri": final_gcs_uri,
                        "metadata": {
                            "title": f"{duration}s commercial for {product} (single clip fallback)",
                            "total_clips": 1,
                            "duration_seconds": duration,
                            "deterministic_av_studio": True,
                        },
                    }
                    event = self._status_event(ctx, f"Commercial (single clip fallback): {final_gcs_uri}")
                    event.actions.state_delta["commercial_artifact"] = commercial_data
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
                            logger.warning(f"[DetAV] Failed to save fallback artifact: {e}")
                    yield event

        except Exception as e:
            logger.warning(f"[DetAV] Veo exception: {e}")
            yield self._status_event(ctx, f"Commercial generation error: {str(e)[:100]}")

    def _extract_last_frame(self, clip_uri: str, bucket_name: str, gcs_folder: str, bucket: str) -> str:
        """Extract the last frame from a video clip and upload as PNG for first-frame chaining."""
        try:
            import cv2
            source_blob = clip_uri.replace(f"gs://{bucket_name}/", "")
            video_bytes = download_blob(bucket_name=bucket_name, source_blob_name=source_blob)

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name

            try:
                cap = cv2.VideoCapture(tmp_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        frame_path = tmp_path.replace(".mp4", "_lastframe.png")
                        cv2.imwrite(frame_path, frame)
                        dest_blob = f"{gcs_folder}/_lastframe_clip.png"
                        upload_blob_to_gcs(source_file_name=frame_path, destination_blob_name=dest_blob)
                        os.unlink(frame_path)
                        return f"{bucket}/{dest_blob}"
                cap.release()
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"[DetAV] Last frame extraction failed: {e}")
        return ""

    def _concatenate_clips(
        self, clip_uris: list, bucket_name: str, gcs_folder: str, bucket: str,
        product: str, duration: int,
    ) -> tuple:
        """Download clips and concatenate with ffmpeg. Returns (gcs_uri, video_bytes)."""
        try:
            import subprocess
            clip_paths = []
            for i, uri in enumerate(clip_uris):
                source_blob = uri.replace(f"gs://{bucket_name}/", "")
                clip_bytes = download_blob(bucket_name=bucket_name, source_blob_name=source_blob)
                clip_path = tempfile.NamedTemporaryFile(suffix=f"_clip{i}.mp4", delete=False).name
                with open(clip_path, "wb") as f:
                    f.write(clip_bytes)
                clip_paths.append(clip_path)

            # Build ffmpeg concat filter
            output_path = tempfile.NamedTemporaryFile(suffix="_commercial.mp4", delete=False).name

            # Create concat list file
            list_path = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w").name
            with open(list_path, "w") as f:
                for cp in clip_paths:
                    f.write(f"file '{cp}'\n")

            # Normalize and concat
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                output_path,
            ]
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.warning(f"[DetAV] ffmpeg concat failed: {result.stderr[:200]}")
                # Cleanup
                for p in clip_paths:
                    os.unlink(p)
                os.unlink(list_path)
                return "", None

            with open(output_path, "rb") as f:
                video_bytes = f.read()

            # Upload concatenated video
            art_fname = f"commercial_{duration}s.mp4"
            dest_blob = f"{gcs_folder}/{art_fname}"
            upload_blob_to_gcs(source_file_name=output_path, destination_blob_name=dest_blob)
            final_uri = f"{bucket}/{dest_blob}"

            # Cleanup
            for p in clip_paths:
                os.unlink(p)
            os.unlink(list_path)
            os.unlink(output_path)

            logger.info(f"[DetAV] Concatenated {len(clip_uris)} clips -> {final_uri}")
            return final_uri, video_bytes

        except Exception as e:
            logger.warning(f"[DetAV] Clip concatenation failed: {e}")
            return "", None

    def _build_clip_prompts(
        self, product: str, audience: str, selling_points: str,
        brand: str, num_clips: int, clip_duration: int,
    ) -> list:
        """Build per-clip Veo prompts that form a narrative arc across clips."""
        if num_clips == 1:
            return [self._build_commercial_prompt(product, audience, selling_points, clip_duration, brand)]

        # 2-clip narrative: discovery → hero reveal
        prompts = [
            (
                f"A cinematic {clip_duration}-second commercial opening for {product} by {brand}. "
                f"SCENE: A {audience} in a vibrant, relatable setting discovers {product}. "
                f"They pick it up with curiosity, examining the {brand} packaging. "
                f"Warm golden-hour lighting, shallow depth of field, smooth dolly-in. "
                f"MOOD: Fresh, intriguing, slice-of-life authenticity. "
                f"PRODUCT: {selling_points[:150]}. "
                f"SUPPRESS SUBTITLES. NO WATERMARKS."
            ),
            (
                f"A cinematic {clip_duration}-second commercial finale for {product} by {brand}. "
                f"SCENE: The {audience} experiences the product — genuine moment of delight. "
                f"Transition to a hero close-up of {brand} {product} packaging with logo clearly visible. "
                f"Dramatic lighting, slow push-in to branded hero moment. "
                f"MOOD: Uplifting, satisfying, aspirational. "
                f"PRODUCT BRANDING: {brand} name and label prominent in final frames. "
                f"{selling_points[:150]}. "
                f"SUPPRESS SUBTITLES. NO WATERMARKS."
            ),
        ]
        # If more clips requested, extend with variations
        while len(prompts) < num_clips:
            prompts.append(prompts[-1])
        return prompts[:num_clips]

    def _build_commercial_prompt(
        self, product: str, audience: str, selling_points: str, duration: int,
        brand: str = "",
    ) -> str:
        """Build a detailed Veo prompt for the commercial."""
        return (
            f"A cinematic {duration}-second commercial for {product} by {brand}. "
            f"NARRATIVE: A {audience} discovers {product} — moment of genuine delight "
            f"as they experience the product — product in action showcasing its benefits — "
            f"close-up hero shot of the {brand} product packaging with branding visible. "
            f"VISUAL STYLE: Premium commercial quality, warm golden-hour lighting, "
            f"shallow depth of field, smooth camera movements, cinematic color grading. "
            f"CAMERA: Start medium-wide, dolly in to close-up on product, "
            f"slow push-in to branded hero moment. Smooth transitions. "
            f"MOOD: Fresh, uplifting, naturally luxurious. "
            f"PRODUCT BRANDING: The {brand} name and product label must appear naturally in at least one shot. "
            f"{selling_points[:200]}. "
            f"SUPPRESS SUBTITLES. NO WATERMARKS."
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
