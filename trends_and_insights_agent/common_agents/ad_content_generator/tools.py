import cv2
import logging
from PIL import Image
from io import BytesIO
import uuid, shutil, time, os
from markdown_pdf import MarkdownPdf, Section

logging.basicConfig(level=logging.INFO)

from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext
from google.genai.types import GenerateVideosConfig, VideoGenerationReferenceImage

from ...shared_libraries.config import config
from ...shared_libraries.utils import (
    download_blob,
    upload_blob_to_gcs,
    download_image_from_gcs,
)
from ...shared_libraries.fidelity_eval.gecko import evaluate as gecko_evaluate

# Get the cloud storage bucket from the environment variable
try:
    GCS_BUCKET = os.environ["BUCKET"]
except KeyError:
    raise Exception("BUCKET environment variable not set")

client = genai.Client()
storage_client = storage.Client()


def save_select_ad_copy(select_ad_copy_dict: dict, tool_context: ToolContext) -> dict:
    """
    Tool to save `select_ad_copy_dict` to the 'final_select_ad_copies' state key.
    Use this tool after the user has selected one or more ad copies to proceed with in ad generation.

    Args:
        select_ad_copy_dict (dict): A dict representing an ad copy specifically selected by the user for ad generation. Use the `tool_context` to extract the following schema:
            name (str): An intuitive name of the ad copy concept.
            headline (str): A concise, attention-grabbing phrase.
            call_to_action (str): A catchy, action-oriented phrase intended for the target audience.
            caption (str): The candidate social media caption proposed for the ad copy.
            body_text (str): The main body of the ad copy. Should be compelling.
            trend_ref (str): The trend(s) referenced in this ad copy (e.g., from the 'target_search_trends' and 'target_yt_trends' state keys).
            rationale (str): A brief rationale explaining why this ad copy will perform well.
        tool_context: The tool context.

    Returns:
        A status message.
    """
    existing_ad_copies = tool_context.state.get("final_select_ad_copies")
    if existing_ad_copies is not {"final_select_ad_copies": []}:
        existing_ad_copies["final_select_ad_copies"].append(select_ad_copy_dict)
    tool_context.state["final_select_ad_copies"] = existing_ad_copies
    return {"status": "ok"}


def save_select_visual_concept(
    select_vis_concept_dict: dict, tool_context: ToolContext
) -> dict:
    """
    Tool to save `select_vis_concept_dict` to the 'final_select_vis_concepts' state key.
    Use this tool after the user has selected one or more visual concepts to proceed with in ad generation.

    Args:
        select_vis_concept_dict (dict): A dict representing a visual concept specifically selected by the user for ad generation. Use the `tool_context` to extract the following schema:
            name (str): An intuitive name of the visual concept.
            type (str): the intended type of creative e.g., "image" or "video".
            trend_ref (str): The trend(s) referenced in this visual concept (e.g., from the 'target_search_trends' and 'target_yt_trends' state keys).
            headline (str): A concise, attention-grabbing phrase.
            call_to_action (str): A catchy, action-oriented phrase intended for the target audience.
            caption (str): The candidate social media caption proposed for the visual concept.
            creative_explain (str): A brief explanation connecting the visual concept to the proposed creative direction.
            rationale (str): A brief rationale explaining why this visual concept will perform well.
            prompt (str): The suggested prompt to generate this creative.
        tool_context: The tool context.

    Returns:
        A status message.
    """
    existing_vis_concepts = tool_context.state.get("final_select_vis_concepts")
    if existing_vis_concepts is not {"final_select_vis_concepts": []}:
        existing_vis_concepts["final_select_vis_concepts"].append(
            select_vis_concept_dict
        )
    tool_context.state["final_select_vis_concepts"] = existing_vis_concepts
    return {"status": "ok"}


async def generate_image(
    prompt: str,
    tool_context: ToolContext,
    concept_name: str,
    number_of_images: int = 1,
) -> dict:
    f"""Generates an image based on the prompt using {config.image_gen_model} via Gemini native image generation.

    Args:
        prompt (str): The prompt to generate the image from.
        tool_context (ToolContext): The tool context.
        concept_name (str, optional): The name of the concept.
        number_of_images (int, optional): The number of images to generate. Defaults to 1.

    Returns:
        dict: Status and the artifact_key of the generated image.

    """
    try:
        response = client.models.generate_content(
            model=config.image_gen_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
    except Exception as e:
        logging.error(f"Image generation failed: {e}")
        return {"status": "failed", "error": str(e)}

    if not response or not response.candidates or not response.candidates[0].content.parts:
        return {"status": "failed"}

    # Create output filename
    if concept_name:
        filename_prefix = f"{concept_name.replace(',', '').replace(' ', '_')}"
    else:
        filename_prefix = f"{str(uuid.uuid4())[:8]}"

    DIR = "session_media"
    SUBDIR = f"{DIR}/imgs"
    if not os.path.exists(SUBDIR):
        os.makedirs(SUBDIR)

    artifact_key = None
    for index, part in enumerate(response.candidates[0].content.parts):
        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
            image_bytes = part.inline_data.data
            artifact_key = f"{filename_prefix}_{index}.png"

            await tool_context.save_artifact(
                filename=artifact_key,
                artifact=types.Part.from_bytes(
                    data=image_bytes, mime_type="image/png"
                ),
            )
            local_filepath = f"{SUBDIR}/{artifact_key}"

            # save the file locally for gcs upload
            image = Image.open(BytesIO(image_bytes))
            image.save(local_filepath)
            gcs_folder = tool_context.state["gcs_folder"]
            artifact_path = os.path.join(gcs_folder, artifact_key)
            logging.info(f"\n\n `generate_image` listdir: {os.listdir('.')}\n\n")

            upload_blob_to_gcs(
                source_file_name=local_filepath,
                destination_blob_name=artifact_path,
            )
            logging.info(
                f"Saved image artifact '{artifact_key}' to folder '{gcs_folder}'"
            )

    try:
        shutil.rmtree(DIR)
        logging.info(f"Directory '{DIR}' and its contents removed successfully")
    except FileNotFoundError:
        logging.exception(f"Directory '{DIR}' not found")
    except OSError as e:
        logging.exception(f"Error removing directory '{DIR}': {e}")

    if artifact_key is None:
        return {"status": "failed", "error": "No image data in response"}

    return {"status": "ok", "artifact_key": f"{artifact_key}"}


async def generate_video(
    prompt: str,
    concept_name: str,
    tool_context: ToolContext,
    number_of_videos: int = 1,
    # aspect_ratio: str = "16:9",
    negative_prompt: str = "",
    existing_image_filename: str = "",
):
    f"""Generates a video based on the prompt for {config.video_gen_model}.

    When `existing_image_filename` is provided, the image is passed as a reference image
    to guide the video generation, ensuring visual consistency with the keyframe.

    Args:
        prompt (str): The prompt to generate the video from.
        concept_name (str, optional): The name of the creative/visual concept.
        tool_context (ToolContext): The tool context.
        number_of_videos (int, optional): The number of videos to generate. Defaults to 1.
        negative_prompt (str, optional): The negative prompt to use. Defaults to "".
        existing_image_filename (str, optional): The artifact_key of a previously generated
            image to use as a reference image for the video. This should be the artifact_key
            returned by `generate_image`. Defaults to "".

    Returns:
        dict: Status and the `artifact_key` of the generated video.
    """
    # Create output filename
    if concept_name:
        filename_prefix = f"{concept_name.replace(",", "").replace(" ", "_")}"
    else:
        filename_prefix = f"{str(uuid.uuid4())[:8]}"

    # Build reference_images list if an existing image is provided as a keyframe
    reference_images = None
    if existing_image_filename != "":
        gcs_folder = tool_context.state.get("gcs_folder", "")
        gcs_location = f"{os.environ['BUCKET']}/{gcs_folder}/{existing_image_filename}"
        reference_images = [
            VideoGenerationReferenceImage(
                image=types.Image(gcs_uri=gcs_location, mime_type="image/png"),
                reference_type="STYLE",
            )
        ]
        logging.info(f"Using reference image for video generation: {gcs_location}")

    gen_config = GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=number_of_videos,
        output_gcs_uri=os.environ["BUCKET"],
        negative_prompt=negative_prompt,
        reference_images=reference_images,
    )
    try:
        operation = client.models.generate_videos(
            model=config.video_gen_model, prompt=prompt, config=gen_config
        )
        while not operation.done:
            time.sleep(15)
            operation = client.operations.get(operation)
            logging.info(operation)
    except Exception as e:
        logging.error(f"Veo generation failed: {e}")
        return {"status": "failed", "error": str(e)}

    if operation.error:
        return {"status": f"failed due to error: {operation.error}"}

    if operation.response:
        if (
            operation.result is not None
            and operation.result.generated_videos is not None
        ):
            for index, generated_video in enumerate(operation.result.generated_videos):
                if (
                    generated_video.video is not None
                    and generated_video.video.uri is not None
                ):
                    video_uri = generated_video.video.uri
                    artifact_key = f"{filename_prefix}_{index}.mp4"

                    BUCKET = os.getenv("BUCKET")
                    if BUCKET is not None:

                        BUCKET_NAME = BUCKET.replace("gs://", "")
                        SOURCE_BLOB = video_uri.replace(BUCKET, "")[1:]

                        video_bytes = download_blob(
                            bucket_name=BUCKET_NAME, source_blob_name=SOURCE_BLOB
                        )
                        logging.info(
                            f"The artifact key for this video is: {artifact_key}"
                        )
                        await tool_context.save_artifact(
                            filename=artifact_key,
                            artifact=types.Part.from_bytes(
                                data=video_bytes, mime_type="video/mp4"
                            ),
                        )

                        # save to common gcs location
                        DESTINATION_BLOB_NAME = (
                            f"{tool_context.state["gcs_folder"]}/{artifact_key}"
                        )
                        bucket = storage_client.get_bucket(BUCKET_NAME)
                        source_blob = bucket.blob(SOURCE_BLOB)
                        destination_bucket = storage_client.get_bucket(BUCKET_NAME)
                        new_blob = bucket.copy_blob(
                            source_blob,
                            destination_bucket,
                            new_name=DESTINATION_BLOB_NAME,
                        )
                        logging.info(
                            f"Blob {source_blob} copied to {destination_bucket}/{new_blob.name}"
                        )

                    return {"status": "ok", "artifact_key": f"{artifact_key}"}


async def save_img_artifact_key(
    artifact_key_dict: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Saves image artifact metadata to the session state for report generation.

    Args:
        artifact_key_dict (dict): Metadata for the generated image.
            artifact_key (str): The filename/key returned by generate_image.
            img_prompt (str): The prompt used.
            concept (str): Creative concept explanation.
            headline (str): Attention-grabbing headline.
            caption (str): Social media caption.
            trend (str): Referenced trend(s).
            rationale_perf (str): Performance rationale.
            audience_appeal (str): Audience appeal.
            markets_product (str): How it markets the product.
            fidelity_score (float): Gecko fidelity score (0.0-1.0) from evaluate_media_fidelity.
        tool_context (ToolContext): The tool context.
    """
    state_key = "img_artifact_keys"
    existing = tool_context.state.get(state_key, {"img_artifact_keys": []})
    existing["img_artifact_keys"].append(artifact_key_dict)
    tool_context.state[state_key] = existing
    return {"status": "ok", "message": f"Saved metadata for {artifact_key_dict.get('artifact_key')}"}


async def save_vid_artifact_key(
    artifact_key_dict: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Saves video artifact metadata to the session state for report generation.

    Args:
        artifact_key_dict (dict): Metadata for the generated video.
            artifact_key (str): The filename/key returned by generate_video.
            vid_prompt (str): The prompt used.
            concept (str): Creative concept explanation.
            headline (str): Attention-grabbing headline.
            caption (str): Social media caption.
            trend (str): Referenced trend(s).
            rationale_perf (str): Performance rationale.
            audience_appeal (str): Audience appeal.
            markets_product (str): How it markets the product.
        tool_context (ToolContext): The tool context.
    """
    state_key = "vid_artifact_keys"
    existing = tool_context.state.get(state_key, {"vid_artifact_keys": []})
    existing["vid_artifact_keys"].append(artifact_key_dict)
    tool_context.state[state_key] = existing
    return {"status": "ok", "message": f"Saved metadata for {artifact_key_dict.get('artifact_key')}"}


def evaluate_media_fidelity(
    media_uri: str,
    ground_truth_description: str,
    media_type: str,
    tool_context: ToolContext,
) -> dict:
    """Evaluate generated image/video fidelity using Gecko scoring.

    Uses Vertex AI's Gecko rubric-based evaluation (GECKO_TEXT2IMAGE / GECKO_TEXT2VIDEO)
    to measure how faithfully generated media represents the product.

    References:
        - Gecko paper: https://arxiv.org/abs/2404.16820
        - product-fidelity-eval: https://github.com/behardja/product-fidelity-eval
        - Vertex AI rubric metrics: https://cloud.google.com/vertex-ai/generative-ai/docs/evaluation/metrics/rubric-based-metrics

    Args:
        media_uri: GCS URI of generated image or video (e.g. gs://bucket/path/file.png).
        ground_truth_description: Product description to evaluate against.
        media_type: "image" or "video".
        tool_context: The tool context.

    Returns:
        dict with score, passing/failing verdicts, and pass/fail decision.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    # Gecko eval uses Vertex AI evaluation API which requires a regional endpoint,
    # not the "global" endpoint used for Gemini 3 models.
    location = "us-central1"

    try:
        result = gecko_evaluate(
            prompt=ground_truth_description,
            media_uri=media_uri,
            media_type=media_type,
            project_id=project_id,
            location=location,
        )
    except Exception as e:
        logging.error(f"Gecko evaluation failed: {e}")
        return {"status": "error", "error": str(e)}

    passed = result.get("score", 0.0) >= 0.7
    result["passed"] = passed

    # Log fidelity score to session state for tracking
    fidelity_log = tool_context.state.get("fidelity_eval_log", [])
    fidelity_log.append({
        "media_uri": media_uri,
        "media_type": media_type,
        "score": result.get("score", 0.0),
        "passed": passed,
    })
    tool_context.state["fidelity_eval_log"] = fidelity_log

    return result


def extract_single_frame(video_path, frame_number, output_image_path) -> str:
    """
    Extracts a single frame from a video at a specified frame number.

    Args:
        video_path (str): The path to the input MP4 video file.
        frame_number (int): The number of the frame to extract (0-indexed).
        output_image_path (str): The path to save the extracted image (e.g., 'frame.jpg').

    Returns:
        str: local path to the extracted image (i.e., frame)
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        logging.info(f"Error: Could not open video file {video_path}")
        return f"Error: Could not open video file {video_path}"

    # Set the frame position
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    ret, frame = cap.read()

    if ret:
        cv2.imwrite(output_image_path, frame)
        logging.info(f"Frame {frame_number} extracted and saved to {output_image_path}")
    else:
        logging.info(f"Error: Could not read frame {frame_number} from {video_path}")

    cap.release()
    cv2.destroyAllWindows()

    return output_image_path


async def save_creatives_and_research_report(tool_context: ToolContext) -> dict:
    """Legacy wrapper — delegates to save_final_report_tool for backward compat.

    Args:
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and the location of the PDF artifact file.
    """
    state = tool_context.state
    processed_report = state.get("combined_final_cited_report", "")
    if not processed_report:
        return {"status": "failed", "error": "No research report found in combined_final_cited_report"}

    img_keys = state.get("img_artifact_keys", {})
    img_artifact_list = img_keys.get("img_artifact_keys", []) if isinstance(img_keys, dict) else img_keys
    vid_keys = state.get("vid_artifact_keys", {})
    vid_artifact_list = vid_keys.get("vid_artifact_keys", []) if isinstance(vid_keys, dict) else vid_keys

    async def _save_artifact(filename, artifact):
        return await tool_context.save_artifact(filename=filename, artifact=artifact)

    result = await save_final_report_tool(
        processed_report=processed_report,
        img_artifact_list=img_artifact_list or [],
        vid_artifact_list=vid_artifact_list or [],
        commercial_artifact=state.get("commercial_artifact", {}),
        focus_group_evaluation=state.get("focus_group_evaluation", ""),
        focus_group_panelists=state.get("focus_group_panelists", {}),
        gcs_folder=state.get("gcs_folder", ""),
        save_artifact_fn=_save_artifact,
    )

    if result.get("status") == "ok":
        tool_context.state["final_report_with_citations"] = processed_report

    return result


async def save_final_report_tool(
    processed_report: str,
    img_artifact_list: list,
    vid_artifact_list: list,
    commercial_artifact: dict,
    focus_group_evaluation: str,
    focus_group_panelists: dict,
    gcs_folder: str,
    save_artifact_fn=None,
) -> dict:
    """Generate the final campaign report PDF with all sections.

    Standalone async function (no ToolContext) for use from BaseAgent orchestrators.
    Includes research report, image/video creatives, commercial info, and focus group results.

    Args:
        processed_report: The research report markdown text.
        img_artifact_list: List of image artifact metadata dicts.
        vid_artifact_list: List of video artifact metadata dicts.
        commercial_artifact: Commercial metadata dict with gcs_uri, metadata, etc.
        focus_group_evaluation: Focus group evaluation text from the LLM.
        focus_group_panelists: Dict with panelist metadata (portraits, testimonials).
        gcs_folder: GCS subfolder for uploads.
        save_artifact_fn: Optional async callable(filename, artifact_part) -> version.

    Returns:
        dict with status and artifact_key.
    """
    try:
        gcs_bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
        DIR = "report_creatives"

        # ==================== #
        # Image creatives section
        # ==================== #
        IMG_SUBDIR = f"{DIR}/imgs"
        os.makedirs(IMG_SUBDIR, exist_ok=True)

        IMG_CREATIVE_STRING = "# Image Creatives\n\n"
        for entry in (img_artifact_list or []):
            logging.info(entry)
            artifact_key = entry.get("artifact_key", "unknown.png")
            gcs_link = os.path.join(gcs_bucket, gcs_folder, artifact_key) if gcs_folder else artifact_key

            LOCAL_FILE_PATH = os.path.join(IMG_SUBDIR, artifact_key)
            try:
                download_image_from_gcs(
                    source_blob_name=os.path.join(gcs_folder, artifact_key),
                    destination_file_name=LOCAL_FILE_PATH,
                )
            except Exception as e:
                logging.warning(f"Could not download image {artifact_key}: {e}")

            IMG_CREATIVE_STRING += f"## {entry.get('headline', 'Untitled')}\n"
            IMG_CREATIVE_STRING += f"*{gcs_link}*\n\n"
            if os.path.exists(LOCAL_FILE_PATH):
                IMG_CREATIVE_STRING += f"![Generated Image]({LOCAL_FILE_PATH})\n\n"
            IMG_CREATIVE_STRING += f"> **Caption:** {entry.get('caption', '')}\n\n"
            IMG_CREATIVE_STRING += f"**Trend(s) Referenced:** `{entry.get('trend', '')}`\n\n"
            IMG_CREATIVE_STRING += f"### Strategic Rationale\n\n"
            IMG_CREATIVE_STRING += f"- **Visual Concept:** {entry.get('concept', '')}\n"
            IMG_CREATIVE_STRING += f"- **Product Strategy:** {entry.get('markets_product', '')}\n"
            IMG_CREATIVE_STRING += f"- **Audience Appeal:** {entry.get('audience_appeal', '')}\n"
            IMG_CREATIVE_STRING += f"- **Performance Logic:** {entry.get('rationale_perf', '')}\n\n"
            if entry.get('fidelity_score') is not None:
                try:
                    IMG_CREATIVE_STRING += f"**Gecko Fidelity Score:** {float(entry['fidelity_score']):.2f} / 1.00\n\n"
                except (ValueError, TypeError):
                    IMG_CREATIVE_STRING += f"**Gecko Fidelity Score:** {entry['fidelity_score']}\n\n"
            IMG_CREATIVE_STRING += f"**AI Generation Prompt:**\n> {entry.get('img_prompt', '')}\n\n"
            IMG_CREATIVE_STRING += "---\n\n"

        # ==================== #
        # Video creatives section
        # ==================== #
        VID_SUBDIR = f"{DIR}/vids"
        os.makedirs(VID_SUBDIR, exist_ok=True)

        VID_CREATIVE_STRING = "# Video Creatives\n\n"
        for entry in (vid_artifact_list or []):
            logging.info(entry)
            artifact_key = entry.get("artifact_key", "unknown.mp4")
            gcs_link = os.path.join(gcs_bucket, gcs_folder, artifact_key) if gcs_folder else artifact_key

            LOCAL_VID_PATH = os.path.join(VID_SUBDIR, artifact_key)
            ARTIFACT_KEY_NAME = artifact_key.replace(".mp4", "")

            try:
                download_image_from_gcs(
                    source_blob_name=os.path.join(gcs_folder, artifact_key),
                    destination_file_name=LOCAL_VID_PATH,
                )
                LOCAL_FRAME_PATH = os.path.join(VID_SUBDIR, f"{ARTIFACT_KEY_NAME}.png")
                LOCAL_VID_FRAME = extract_single_frame(LOCAL_VID_PATH, 1, LOCAL_FRAME_PATH)
            except Exception as e:
                logging.warning(f"Could not download/extract video {artifact_key}: {e}")
                LOCAL_VID_FRAME = None

            VID_CREATIVE_STRING += f"## {entry.get('headline', 'Untitled')}\n"
            VID_CREATIVE_STRING += f"*{gcs_link}*\n\n"
            if LOCAL_VID_FRAME and os.path.exists(LOCAL_VID_FRAME):
                VID_CREATIVE_STRING += f"![Video Thumbnail]({LOCAL_VID_FRAME})\n\n"
            VID_CREATIVE_STRING += f"> **Caption:** {entry.get('caption', '')}\n\n"
            VID_CREATIVE_STRING += f"**Trend(s) Referenced:** `{entry.get('trend', '')}`\n\n"
            VID_CREATIVE_STRING += f"### Strategic Rationale\n\n"
            VID_CREATIVE_STRING += f"- **Visual Concept:** {entry.get('concept', '')}\n"
            VID_CREATIVE_STRING += f"- **Product Strategy:** {entry.get('markets_product', '')}\n"
            VID_CREATIVE_STRING += f"- **Audience Appeal:** {entry.get('audience_appeal', '')}\n"
            VID_CREATIVE_STRING += f"- **Performance Logic:** {entry.get('rationale_perf', '')}\n\n"
            VID_CREATIVE_STRING += f"**AI Generation Prompt:**\n> {entry.get('vid_prompt', '')}\n\n"
            VID_CREATIVE_STRING += "---\n\n"

        # ==================== #
        # Commercial section
        # ==================== #
        COMMERCIAL_STRING = "# Commercial\n\n"
        if commercial_artifact and isinstance(commercial_artifact, dict):
            gcs_uri = commercial_artifact.get("gcs_uri", "")
            metadata = commercial_artifact.get("metadata", {})
            if isinstance(metadata, dict):
                COMMERCIAL_STRING += f"## {metadata.get('title', 'Campaign Commercial')}\n\n"
                COMMERCIAL_STRING += f"**Duration:** {metadata.get('duration_seconds', 'N/A')}s\n\n"
                COMMERCIAL_STRING += f"**Total Clips:** {metadata.get('total_clips', 'N/A')}\n\n"
                if gcs_uri:
                    COMMERCIAL_STRING += f"**GCS Location:** `{gcs_uri}`\n\n"
                if metadata.get("narrative_arc"):
                    COMMERCIAL_STRING += f"**Narrative Arc:** {metadata['narrative_arc']}\n\n"
                if metadata.get("trend_connections"):
                    COMMERCIAL_STRING += f"**Trend Connections:** {metadata['trend_connections']}\n\n"
                if metadata.get("target_audience_appeal"):
                    COMMERCIAL_STRING += f"**Target Audience Appeal:** {metadata['target_audience_appeal']}\n\n"
                scenes = metadata.get("scene_descriptions", [])
                if scenes:
                    COMMERCIAL_STRING += "### Scene Breakdown\n\n"
                    for idx, scene in enumerate(scenes, 1):
                        COMMERCIAL_STRING += f"{idx}. {scene}\n"
                    COMMERCIAL_STRING += "\n"
                COMMERCIAL_STRING += f"**Has Audio:** {'Yes' if metadata.get('has_audio') else 'No'}\n\n"
            else:
                COMMERCIAL_STRING += f"**GCS Location:** `{gcs_uri}`\n\n"
        else:
            COMMERCIAL_STRING += "*No commercial was produced.*\n\n"
        COMMERCIAL_STRING += "---\n\n"

        # ==================== #
        # Focus group section
        # ==================== #
        FOCUS_GROUP_STRING = "# Focus Group Evaluation\n\n"
        if focus_group_evaluation:
            FOCUS_GROUP_STRING += focus_group_evaluation + "\n\n"
        else:
            FOCUS_GROUP_STRING += "*No focus group evaluation was conducted.*\n\n"

        # Add panelist info with links to portraits and testimonials
        panelists = focus_group_panelists.get("panelists", []) if isinstance(focus_group_panelists, dict) else []
        if panelists:
            FOCUS_GROUP_STRING += "## Panelist Profiles\n\n"
            for p in panelists:
                FOCUS_GROUP_STRING += f"### {p.get('name', 'Unknown')}, Age {p.get('age', 'N/A')}\n"
                FOCUS_GROUP_STRING += f"**Persona:** {p.get('persona', '')}\n\n"
                if p.get("portrait_gcs_uri"):
                    FOCUS_GROUP_STRING += f"**Portrait:** `{p['portrait_gcs_uri']}`\n\n"
                if p.get("testimonial_video_gcs_uri"):
                    FOCUS_GROUP_STRING += f"**Testimonial Video:** `{p['testimonial_video_gcs_uri']}`\n\n"
                if p.get("voiceover_gcs_uri"):
                    FOCUS_GROUP_STRING += f"**Voiceover:** `{p['voiceover_gcs_uri']}`\n\n"
                FOCUS_GROUP_STRING += "---\n\n"

        # ==================== #
        # Create PDF
        # ==================== #
        artifact_key = "final_trends_and_creatives_report.pdf"
        report_filepath = f"{DIR}/{artifact_key}"

        pdf = MarkdownPdf(toc_level=4)
        pdf.add_section(Section(f" {processed_report}\n"))
        pdf.add_section(
            Section(f"# Ad Creatives\n\n{IMG_CREATIVE_STRING}\n\n{VID_CREATIVE_STRING}")
        )
        pdf.add_section(Section(COMMERCIAL_STRING))
        pdf.add_section(Section(FOCUS_GROUP_STRING))
        pdf.meta["title"] = "[Final] Trends-to-Creatives Campaign Report"
        pdf.save(report_filepath)

        with open(report_filepath, "rb") as f:
            document_bytes = f.read()

        document_part = types.Part(
            inline_data=types.Blob(data=document_bytes, mime_type="application/pdf")
        )

        version = None
        if save_artifact_fn:
            version = await save_artifact_fn(artifact_key, document_part)

        if gcs_folder:
            upload_blob_to_gcs(
                source_file_name=report_filepath,
                destination_blob_name=os.path.join(gcs_folder, artifact_key),
            )

        logging.info(
            f"\n\nSaved final report '{artifact_key}', version {version}, to folder '{gcs_folder}'\n\n"
        )

        shutil.rmtree(DIR)
        return {
            "status": "ok",
            "artifact_key": artifact_key,
            "message": "Final campaign report saved as PDF with all sections.",
        }
    except Exception as e:
        logging.error(f"Error saving final report: {e}")
        return {"status": "failed", "error": str(e)}


# TODO: Get ffmpeg install working on agent engine
# async def concatenate_videos(
#     video_filenames: List[str],
#     tool_context: ToolContext,
#     concept_name: str,
# ):
#     """Concatenates multiple videos into a single longer video for a concept.

#     Args:
#         video_filenames (List[str]): List of video filenames from tool_context artifacts.
#         tool_context (ToolContext): The tool context.
#         concept_name (str, optional): The name of the concept.

#     Returns:
#         dict: Status and the location of the concatenated video file.
#     """
#     if not video_filenames:
#         return {"status": "failed", "error": "No video filenames provided"}

#     try:
#         # Create temporary directory for processing
#         with tempfile.TemporaryDirectory() as temp_dir:
#             # Load videos from artifacts and save locally
#             local_video_paths = []
#             for idx, video_filename in enumerate(video_filenames):
#                 # Load artifact
#                 video_part = await tool_context.load_artifact(video_filename)
#                 if not video_part:
#                     return {
#                         "status": "failed",
#                         "error": f"Could not load artifact: {video_filename}",
#                     }
#                 if not video_part.inline_data:
#                     return {
#                         "status": "failed",
#                         "error": f"Could not load artifact inline_data: {video_filename}",
#                     }
#                 if not video_part.inline_data.data:
#                     return {
#                         "status": "failed",
#                         "error": f"Could not load artifact inline_data.data: {video_filename}",
#                     }

#                 # Extract bytes from the Part object
#                 video_bytes = video_part.inline_data.data

#                 # Save locally for ffmpeg processing
#                 local_path = os.path.join(temp_dir, f"video_{idx}.mp4")
#                 with open(local_path, "wb") as f:
#                     f.write(video_bytes)
#                 local_video_paths.append(local_path)

#             # Create output filename
#             if concept_name:
#                 output_filename = f"{concept_name}.mp4"
#             else:
#                 output_filename = f"{uuid.uuid4()}.mp4"

#             output_path = os.path.join(temp_dir, output_filename)

#             if len(local_video_paths) == 1:
#                 # If only one video, just copy it
#                 subprocess.run(["cp", local_video_paths[0], output_path], check=True)
#             else:
#                 # Create ffmpeg filter complex for concatenation with transitions
#                 # Simple concatenation without transitions
#                 concat_file = os.path.join(temp_dir, "concat_list.txt")
#                 with open(concat_file, "w") as f:
#                     for video_path in local_video_paths:
#                         f.write(f"file '{video_path}'\n")

#                 subprocess.run(
#                     [
#                         "ffmpeg",
#                         "-f",
#                         "concat",
#                         "-safe",
#                         "0",
#                         "-i",
#                         concat_file,
#                         "-c",
#                         "copy",
#                         output_path,
#                     ],
#                     check=True,
#                     capture_output=True,
#                     text=True,
#                 )

#             # Read the output video
#             with open(output_path, "rb") as f:
#                 video_bytes = f.read()

#             # Save as artifact
#             await tool_context.save_artifact(
#                 output_filename,
#                 types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
#             )

#             # Also upload to GCS for persistence
#             gcs_uri = upload_file_to_gcs(
#                 file_path=output_filename,
#                 file_data=video_bytes,
#                 content_type="video/mp4",
#             )
#             new_entry = {output_filename: gcs_uri}
#             tool_context.state["artifact_keys"]["video_creatives"].update(new_entry)

#             return {
#                 "status": "ok",
#                 "video_filename": output_filename,
#                 "gcs_uri": gcs_uri,
#                 "num_videos_concatenated": len(video_filenames),
#             }

#     except subprocess.CalledProcessError as e:
#         return {
#             "status": "failed",
#             "error": f"FFmpeg error: {e.stderr if hasattr(e, 'stderr') else str(e)}",
#         }
#     except Exception as e:
#         return {"status": "failed", "error": str(e)}
