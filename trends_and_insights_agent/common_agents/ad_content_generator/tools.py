import cv2
import logging
from PIL import Image
from io import BytesIO
import uuid, shutil, time, os
from markdown_pdf import MarkdownPdf, Section
from fpdf import FPDF
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)

from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext
from google.genai.types import GenerateVideosConfig

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
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=config.image_gen_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )
                break
            except Exception as gen_err:
                err_str = str(gen_err)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    import time
                    wait = 15 * (attempt + 1)
                    logging.warning(f"Image gen rate limited, waiting {wait}s (attempt {attempt + 1}/3)")
                    time.sleep(wait)
                else:
                    raise
        if response is None:
            return {"status": "failed", "error": "Rate limited after 3 retries"}
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

    # Auto-save img_artifact_key so orchestrator sees the image even if
    # the LLM doesn't get a chance to call save_img_artifact_key separately
    # (AE wave may end before the next tool call)
    auto_metadata = {
        "artifact_key": artifact_key,
        "img_prompt": prompt[:500],
        "concept": concept_name or "",
        "headline": "",
        "caption": "",
        "auto_saved": True,
    }
    state_key = "img_artifact_keys"
    existing = tool_context.state.get(state_key, {"img_artifact_keys": []})
    prev_list = list(existing.get("img_artifact_keys", []) if isinstance(existing, dict) else existing)
    # Avoid duplicates
    existing_keys = {item.get("artifact_key") for item in prev_list if isinstance(item, dict)}
    if artifact_key not in existing_keys:
        prev_list.append(auto_metadata)
        tool_context.state[state_key] = {"img_artifact_keys": prev_list}
        logging.info(f"Auto-saved img_artifact_key: {artifact_key} (total: {len(prev_list)})")

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

    # Build first-frame image conditioning if an existing image is provided as a keyframe.
    # NOTE: Veo 3.1 does not support reference_images with reference_type="STYLE".
    # Instead, pass the image as the `image` parameter (first-frame conditioning).
    first_frame_image = None
    if existing_image_filename != "":
        gcs_folder = tool_context.state.get("gcs_folder", "")
        gcs_location = f"{os.environ['BUCKET']}/{gcs_folder}/{existing_image_filename}"
        first_frame_image = types.Image(gcs_uri=gcs_location, mime_type="image/png")
        logging.info(f"Using first-frame image for video generation: {gcs_location}")

    gen_config = GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=number_of_videos,
        output_gcs_uri=os.environ["BUCKET"],
        negative_prompt=negative_prompt,
    )
    try:
        if first_frame_image:
            operation = client.models.generate_videos(
                model=config.video_gen_model, prompt=prompt, image=first_frame_image, config=gen_config
            )
        else:
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
    # Create a NEW list/dict to ensure ADK state tracking detects the change
    prev_list = list(existing.get("img_artifact_keys", []) if isinstance(existing, dict) else existing)
    prev_list.append(artifact_key_dict)
    tool_context.state[state_key] = {"img_artifact_keys": prev_list}
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
    # Create a NEW list/dict to ensure ADK state tracking detects the change
    prev_list = list(existing.get("vid_artifact_keys", []) if isinstance(existing, dict) else existing)
    prev_list.append(artifact_key_dict)
    tool_context.state[state_key] = {"vid_artifact_keys": prev_list}
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

    # If media_uri is not a full GCS URI, construct it from artifact_key + gcs_folder
    if not media_uri.startswith("gs://"):
        gcs_folder = tool_context.state.get("gcs_folder", "")
        bucket = os.environ.get("BUCKET", "gs://zghost-media-center")
        if gcs_folder:
            media_uri = f"{bucket}/{gcs_folder}/{media_uri}"
        else:
            media_uri = f"{bucket}/{media_uri}"
        logging.info(f"Gecko eval: constructed GCS URI: {media_uri}")

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


def extract_multiple_frames(video_path, num_frames=4, output_dir=".") -> list:
    """
    Extracts multiple evenly-spaced frames from a video.

    Args:
        video_path (str): The path to the input MP4 video file.
        num_frames (int): Number of frames to extract (default 4).
        output_dir (str): Directory to save frames.

    Returns:
        list: Paths to extracted frame images.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logging.warning(f"Could not open video file {video_path}")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < num_frames:
        num_frames = total_frames

    if total_frames == 0:
        cap.release()
        return []

    # Calculate evenly spaced frame numbers
    frame_indices = [int(i * total_frames / (num_frames + 1)) for i in range(1, num_frames + 1)]

    extracted_paths = []
    for idx, frame_num in enumerate(frame_indices):
        output_path = os.path.join(output_dir, f"frame_{idx}.jpg")
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(output_path, frame)
            extracted_paths.append(output_path)
            logging.info(f"Extracted frame {frame_num} to {output_path}")

    cap.release()
    cv2.destroyAllWindows()
    return extracted_paths


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
    brand: str = "",
    product: str = "",
    audience: str = "",
    selling_points: str = "",
    target_search_trends: str = "",
    target_yt_trends: str = "",
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
        brand: Brand name (e.g., "Tide").
        product: Product name (e.g., "Tide Fabric Softener").
        audience: Target audience (e.g., "Gen Z eco-conscious consumers").
        selling_points: Key product features.
        target_search_trends: Google Search trends that drove the campaign.
        target_yt_trends: YouTube trends that drove the campaign.

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
        # Create PDF with fpdf2
        # ==================== #
        pdf_artifact_key = "final_trends_and_creatives_report.pdf"
        artifact_key = pdf_artifact_key
        report_filepath = f"{DIR}/{pdf_artifact_key}"

        def _sanitize_text(text: str) -> str:
            """Replace Unicode characters unsupported by Helvetica (Latin-1) with safe equivalents."""
            replacements = {
                "\u2014": "-", "\u2013": "-",  # em-dash, en-dash
                "\u2018": "'", "\u2019": "'",  # smart quotes
                "\u201c": '"', "\u201d": '"',  # smart double quotes
                "\u2026": "...",  # ellipsis
                "\u2022": "-",  # bullet
                "\u2713": "[x]", "\u2717": "[ ]",  # check/cross marks
                "\u2192": "->", "\u2190": "<-",  # arrows
                "\u00a0": " ",  # non-breaking space
                "\u200b": "",  # zero-width space
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            # Final fallback: encode to latin-1 replacing unknown chars
            return text.encode("latin-1", errors="replace").decode("latin-1")

        # Brand and product info — prefer explicit params, fallback to extraction
        brand_name = brand or "Campaign Report"
        product_name = product or ""
        campaign_tagline = ""

        if not product_name:
            # Fallback: extract from commercial metadata or report
            if commercial_artifact and isinstance(commercial_artifact, dict):
                metadata = commercial_artifact.get("metadata", {})
                if isinstance(metadata, dict) and metadata.get("title"):
                    product_name = metadata["title"]
            if not product_name and processed_report:
                first_line = processed_report.strip().split("\n")[0].strip()
                if ":" in first_line:
                    product_name = first_line.split(":", 1)[1].strip()[:60]
                elif first_line.startswith("#"):
                    product_name = first_line.lstrip("# ").strip()[:60]

        # Campaign tagline from image headlines or selling points
        if img_artifact_list and len(img_artifact_list) > 0:
            first_img = img_artifact_list[0]
            if first_img.get("headline"):
                campaign_tagline = first_img["headline"]
        if not campaign_tagline and selling_points:
            campaign_tagline = selling_points[:80]

        # Custom PDF class with headers/footers and auto Unicode sanitization
        class CampaignPDF(FPDF):
            def __init__(self):
                super().__init__()
                self.is_cover = False
                self.is_back_cover = False

            def cell(self, w=0, h=None, text="", *args, **kwargs):
                return super().cell(w, h, _sanitize_text(str(text)), *args, **kwargs)

            def multi_cell(self, w, h=None, text="", *args, **kwargs):
                return super().multi_cell(w, h, _sanitize_text(str(text)), *args, **kwargs)

            def header(self):
                if self.is_cover or self.is_back_cover:
                    return
                # Header with brand color bar
                self.set_fill_color(0, 51, 160)  # #0033A0
                self.rect(0, 0, 210, 8, 'F')
                self.set_y(10)

            def footer(self):
                if self.is_cover or self.is_back_cover:
                    return
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

        branded_pdf_ok = True
        try:
            pdf = CampaignPDF()
            pdf.set_auto_page_break(auto=True, margin=15)

            # ==================== #
            # 1. COVER PAGE
            # ==================== #
            pdf.is_cover = True
            pdf.add_page()

            # Top accent bar
            pdf.set_fill_color(0, 51, 160)  # #0033A0
            pdf.rect(0, 0, 210, 30, 'F')

            # Title area
            pdf.set_y(50)
            pdf.set_font('Helvetica', 'B', 32)
            pdf.set_text_color(0, 51, 160)
            pdf.cell(0, 15, brand_name, 0, 1, 'C')

            pdf.set_font('Helvetica', '', 24)
            pdf.set_text_color(32, 33, 36)
            pdf.cell(0, 12, product_name, 0, 1, 'C')

            if campaign_tagline:
                pdf.set_y(pdf.get_y() + 5)
                pdf.set_font('Helvetica', 'I', 14)
                pdf.set_text_color(100, 100, 100)
                # Truncate long taglines
                if len(campaign_tagline) > 80:
                    campaign_tagline = campaign_tagline[:77] + "..."
                pdf.multi_cell(0, 8, campaign_tagline, 0, 'C')

            # Hero image if available
            if img_artifact_list and len(img_artifact_list) > 0:
                first_img_key = img_artifact_list[0].get("artifact_key", "")
                hero_path = os.path.join(IMG_SUBDIR, first_img_key)
                if os.path.exists(hero_path):
                    pdf.set_y(120)
                    try:
                        # Center image, max width 140mm
                        pdf.image(hero_path, x=35, w=140)
                    except Exception as e:
                        logging.warning(f"Could not embed hero image: {e}")

            # Footer info
            pdf.set_y(250)
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, f"Campaign Report — {datetime.now().strftime('%B %d, %Y')}", 0, 1, 'C')
            pdf.cell(0, 5, "Prepared by Trends & Insights AI", 0, 1, 'C')

            pdf.is_cover = False

            # ==================== #
            # 2. EXECUTIVE SUMMARY
            # ==================== #
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 18)
            pdf.set_text_color(0, 51, 160)
            pdf.cell(0, 10, "Executive Summary", 0, 1)
            pdf.ln(3)

            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(32, 33, 36)

            # Extract key findings from research report (first few sentences or bullets)
            key_findings = []
            if processed_report:
                # Try to extract bullet points or first few sentences
                lines = processed_report.split('\n')
                for line in lines[:30]:  # Check first 30 lines
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('* '):
                        key_findings.append(line[2:].strip())
                        if len(key_findings) >= 3:
                            break

                # If no bullets found, extract first few sentences
                if not key_findings:
                    sentences = re.split(r'[.!?]\s+', processed_report[:500])
                    key_findings = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]

            if key_findings:
                pdf.set_font('Helvetica', 'B', 11)
                pdf.cell(0, 6, "Key Findings:", 0, 1)
                pdf.set_font('Helvetica', '', 10)
                for finding in key_findings:
                    pdf.multi_cell(0, 5, f"• {finding[:200]}", 0)
                    pdf.ln(2)
            else:
                pdf.multi_cell(0, 5, "Comprehensive market research and trend analysis conducted.", 0)
                pdf.ln(2)

            pdf.ln(3)

            # Campaign metrics summary
            pdf.set_fill_color(248, 249, 250)  # #F8F9FA light gray background
            pdf.rect(10, pdf.get_y(), 190, 40, 'F')
            pdf.ln(5)

            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(0, 6, "Campaign Assets:", 0, 1)
            pdf.set_font('Helvetica', '', 10)

            metrics_y = pdf.get_y()
            pdf.set_xy(15, metrics_y)
            pdf.cell(90, 5, f"Images Generated: {len(img_artifact_list or [])}", 0, 0)
            pdf.set_x(105)
            pdf.cell(90, 5, f"Videos Generated: {len(vid_artifact_list or [])}", 0, 1)

            pdf.set_x(15)
            has_commercial = bool(commercial_artifact and commercial_artifact.get("gcs_uri"))
            pdf.cell(90, 5, f"Commercial: {'Yes' if has_commercial else 'No'}", 0, 0)

            # Focus group verdict
            focus_verdict = "Not conducted"
            if focus_group_evaluation:
                if "go decision" in focus_group_evaluation.lower() or "approve" in focus_group_evaluation.lower():
                    focus_verdict = "GO"
                elif "no-go" in focus_group_evaluation.lower() or "reject" in focus_group_evaluation.lower():
                    focus_verdict = "NO-GO"
                else:
                    focus_verdict = "Completed"

            pdf.set_x(105)
            pdf.cell(90, 5, f"Focus Group: {focus_verdict}", 0, 1)

            pdf.ln(10)

            # ==================== #
            # 2b. CAMPAIGN CONTEXT & TRENDS
            # ==================== #
            if brand or audience or target_search_trends or target_yt_trends:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 18)
                pdf.set_text_color(0, 51, 160)
                pdf.cell(0, 10, "Campaign Context & Trend Drivers", 0, 1)
                pdf.ln(3)

                # Campaign brief box
                pdf.set_fill_color(240, 245, 255)  # Light blue
                box_y = pdf.get_y()
                pdf.rect(10, box_y, 190, 50, 'F')
                pdf.set_xy(15, box_y + 5)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(0, 51, 160)
                pdf.cell(0, 6, "Campaign Brief", 0, 1)
                pdf.set_x(15)
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(32, 33, 36)
                if brand:
                    pdf.set_x(15)
                    pdf.cell(90, 5, f"Brand: {brand}", 0, 0)
                if audience:
                    pdf.set_x(105)
                    pdf.cell(90, 5, f"Audience: {audience[:50]}", 0, 1)
                if product:
                    pdf.set_x(15)
                    pdf.cell(0, 5, f"Product: {product}", 0, 1)
                if selling_points:
                    pdf.set_x(15)
                    pdf.multi_cell(180, 5, f"Key Features: {selling_points[:200]}", 0)
                pdf.set_y(box_y + 55)

                # Trends
                if target_search_trends:
                    pdf.set_font('Helvetica', 'B', 12)
                    pdf.set_text_color(26, 115, 232)
                    pdf.cell(0, 7, "Google Search Trends", 0, 1)
                    pdf.set_font('Helvetica', '', 10)
                    pdf.set_text_color(32, 33, 36)
                    trend_text = target_search_trends if isinstance(target_search_trends, str) else str(target_search_trends)
                    for trend_line in trend_text.split('\n')[:10]:
                        if trend_line.strip():
                            pdf.set_x(15)
                            pdf.multi_cell(0, 5, f"• {trend_line.strip()[:150]}", 0)
                    pdf.ln(3)

                if target_yt_trends:
                    pdf.set_font('Helvetica', 'B', 12)
                    pdf.set_text_color(26, 115, 232)
                    pdf.cell(0, 7, "YouTube Trends", 0, 1)
                    pdf.set_font('Helvetica', '', 10)
                    pdf.set_text_color(32, 33, 36)
                    yt_text = target_yt_trends if isinstance(target_yt_trends, str) else str(target_yt_trends)
                    for yt_line in yt_text.split('\n')[:10]:
                        if yt_line.strip():
                            pdf.set_x(15)
                            pdf.multi_cell(0, 5, f"• {yt_line.strip()[:150]}", 0)
                    pdf.ln(3)

            # ==================== #
            # 3. RESEARCH HIGHLIGHTS
            # ==================== #
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 18)
            pdf.set_text_color(0, 51, 160)
            pdf.cell(0, 10, "Research Highlights", 0, 1)
            pdf.ln(3)

            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(32, 33, 36)

            if processed_report:
                # Simple markdown parsing for headers and bullets
                lines = processed_report.split('\n')
                for line in lines:
                    line_stripped = line.strip()

                    # Headers
                    if line_stripped.startswith('## '):
                        pdf.ln(3)
                        pdf.set_font('Helvetica', 'B', 13)
                        pdf.set_text_color(26, 115, 232)  # #1A73E8 Google blue
                        pdf.multi_cell(0, 6, line_stripped[3:], 0)
                        pdf.set_font('Helvetica', '', 10)
                        pdf.set_text_color(32, 33, 36)
                        pdf.ln(1)
                    elif line_stripped.startswith('### '):
                        pdf.ln(2)
                        pdf.set_font('Helvetica', 'B', 11)
                        pdf.multi_cell(0, 5, line_stripped[4:], 0)
                        pdf.set_font('Helvetica', '', 10)
                        pdf.ln(1)
                    elif line_stripped.startswith('# ') and not line_stripped.startswith('## '):
                        pdf.ln(4)
                        pdf.set_font('Helvetica', 'B', 15)
                        pdf.set_text_color(0, 51, 160)
                        pdf.multi_cell(0, 7, line_stripped[2:], 0)
                        pdf.set_font('Helvetica', '', 10)
                        pdf.set_text_color(32, 33, 36)
                        pdf.ln(2)
                    # Bullets
                    elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
                        pdf.set_x(15)
                        pdf.multi_cell(0, 5, f"• {line_stripped[2:]}", 0)
                    # Bold text — strip markers and render as regular text
                    elif '**' in line_stripped:
                        clean = line_stripped.replace('**', '')
                        if clean.strip():
                            pdf.multi_cell(0, 5, clean, 0)
                    # Regular text
                    elif line_stripped:
                        pdf.multi_cell(0, 5, line_stripped, 0)
                    else:
                        pdf.ln(2)
            else:
                pdf.multi_cell(0, 5, "No research report available.", 0)

            # ==================== #
            # 4. CREATIVE PORTFOLIO
            # ==================== #
            if img_artifact_list or vid_artifact_list:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 18)
                pdf.set_text_color(0, 51, 160)
                pdf.cell(0, 10, "Creative Portfolio", 0, 1)
                pdf.ln(5)

            # Images
            for idx, entry in enumerate(img_artifact_list or []):
                if idx > 0:
                    pdf.add_page()

                artifact_key = entry.get("artifact_key", "")
                img_path = os.path.join(IMG_SUBDIR, artifact_key)

                pdf.set_font('Helvetica', 'B', 14)
                pdf.set_text_color(26, 115, 232)
                headline = entry.get("headline", "Untitled")
                pdf.multi_cell(0, 7, headline, 0)
                pdf.ln(2)

                # Image
                if os.path.exists(img_path):
                    try:
                        pdf.image(img_path, x=10, w=190)
                        pdf.ln(3)
                    except Exception as e:
                        logging.warning(f"Could not embed image {artifact_key}: {e}")

                # Fidelity score badge
                fidelity = entry.get("fidelity_score")
                if fidelity is not None:
                    try:
                        score = float(fidelity)
                        if score >= 0.7:
                            badge_color = (52, 168, 83)  # Green
                            badge_text = "High Fidelity"
                        elif score >= 0.5:
                            badge_color = (251, 188, 4)  # Yellow
                            badge_text = "Medium Fidelity"
                        else:
                            badge_color = (234, 67, 53)  # Red
                            badge_text = "Low Fidelity"

                        pdf.set_fill_color(*badge_color)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font('Helvetica', 'B', 9)
                        badge_width = pdf.get_string_width(f"{badge_text}: {score:.2f}") + 6
                        pdf.cell(badge_width, 6, f"{badge_text}: {score:.2f}", 0, 1, 'L', True)
                        pdf.ln(2)
                        pdf.set_text_color(32, 33, 36)
                    except (ValueError, TypeError):
                        pass

                # Caption
                pdf.set_font('Helvetica', 'I', 10)
                pdf.set_text_color(80, 80, 80)
                caption = entry.get("caption", "")
                if caption:
                    pdf.multi_cell(0, 5, caption, 0)
                    pdf.ln(2)

                # Concept rationale
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(32, 33, 36)
                concept = entry.get("concept", "")
                if concept:
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.cell(0, 5, "Concept:", 0, 1)
                    pdf.set_font('Helvetica', '', 10)
                    pdf.multi_cell(0, 5, concept, 0)
                    pdf.ln(2)

                # AI prompt (smaller gray text)
                prompt = entry.get("img_prompt", "")
                if prompt:
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(128, 128, 128)
                    pdf.multi_cell(0, 4, f"AI Prompt: {prompt[:300]}", 0)

            # Videos
            for idx, entry in enumerate(vid_artifact_list or []):
                pdf.add_page()

                artifact_key = entry.get("artifact_key", "")
                vid_path = os.path.join(VID_SUBDIR, artifact_key)

                pdf.set_font('Helvetica', 'B', 14)
                pdf.set_text_color(26, 115, 232)
                headline = entry.get("headline", "Untitled Video")
                pdf.multi_cell(0, 7, headline, 0)
                pdf.ln(2)

                # Video thumbnail
                if os.path.exists(vid_path):
                    frame_path = os.path.join(VID_SUBDIR, artifact_key.replace(".mp4", ".png"))
                    if os.path.exists(frame_path):
                        try:
                            pdf.image(frame_path, x=10, w=190)
                            pdf.ln(3)
                        except Exception as e:
                            logging.warning(f"Could not embed video frame: {e}")

                # Caption and details (similar to images)
                pdf.set_font('Helvetica', 'I', 10)
                pdf.set_text_color(80, 80, 80)
                caption = entry.get("caption", "")
                if caption:
                    pdf.multi_cell(0, 5, caption, 0)
                    pdf.ln(2)

                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(32, 33, 36)
                concept = entry.get("concept", "")
                if concept:
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.cell(0, 5, "Concept:", 0, 1)
                    pdf.set_font('Helvetica', '', 10)
                    pdf.multi_cell(0, 5, concept, 0)

            # ==================== #
            # 5. COMMERCIAL STORYBOARD
            # ==================== #
            if commercial_artifact and commercial_artifact.get("gcs_uri"):
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 18)
                pdf.set_text_color(0, 51, 160)
                pdf.cell(0, 10, "Commercial Storyboard", 0, 1)
                pdf.ln(3)

                metadata = commercial_artifact.get("metadata", {})
                if isinstance(metadata, dict):
                    pdf.set_font('Helvetica', 'B', 12)
                    pdf.set_text_color(32, 33, 36)
                    title = metadata.get("title", "Campaign Commercial")
                    pdf.cell(0, 6, title, 0, 1)

                    pdf.set_font('Helvetica', '', 10)
                    duration = metadata.get("duration_seconds", "N/A")
                    pdf.cell(0, 5, f"Duration: {duration}s", 0, 1)
                    pdf.ln(2)

                # Extract 4 frames from commercial
                gcs_uri = commercial_artifact.get("gcs_uri", "")
                if gcs_uri:
                    # Download commercial if not already downloaded
                    commercial_filename = os.path.basename(gcs_uri)
                    commercial_local_path = os.path.join(VID_SUBDIR, commercial_filename)

                    if not os.path.exists(commercial_local_path):
                        try:
                            # Extract just the blob path from GCS URI
                            blob_path = gcs_uri.replace(gcs_bucket + "/", "")
                            download_image_from_gcs(
                                source_blob_name=blob_path,
                                destination_file_name=commercial_local_path,
                            )
                        except Exception as e:
                            logging.warning(f"Could not download commercial for storyboard: {e}")

                    # Extract 4 frames
                    if os.path.exists(commercial_local_path):
                        frame_dir = os.path.join(VID_SUBDIR, "storyboard_frames")
                        os.makedirs(frame_dir, exist_ok=True)

                        frame_paths = extract_multiple_frames(commercial_local_path, num_frames=4, output_dir=frame_dir)

                        if frame_paths:
                            scenes = metadata.get("scene_descriptions", []) if isinstance(metadata, dict) else []

                            # Display frames in 2x2 grid
                            for i in range(0, len(frame_paths), 2):
                                row_y = pdf.get_y()

                                # Left frame
                                if i < len(frame_paths):
                                    try:
                                        pdf.image(frame_paths[i], x=10, y=row_y, w=90)
                                        pdf.set_xy(10, row_y + 55)
                                        pdf.set_font('Helvetica', 'I', 8)
                                        pdf.set_text_color(80, 80, 80)
                                        scene_desc = scenes[i] if i < len(scenes) else f"Frame {i+1}"
                                        pdf.multi_cell(90, 4, scene_desc[:150], 0)
                                    except Exception as e:
                                        logging.warning(f"Could not embed storyboard frame {i}: {e}")

                                # Right frame
                                if i + 1 < len(frame_paths):
                                    try:
                                        pdf.image(frame_paths[i+1], x=110, y=row_y, w=90)
                                        pdf.set_xy(110, row_y + 55)
                                        pdf.set_font('Helvetica', 'I', 8)
                                        pdf.set_text_color(80, 80, 80)
                                        scene_desc = scenes[i+1] if i+1 < len(scenes) else f"Frame {i+2}"
                                        pdf.multi_cell(90, 4, scene_desc[:150], 0)
                                    except Exception as e:
                                        logging.warning(f"Could not embed storyboard frame {i+1}: {e}")

                                pdf.set_y(row_y + 70)
                                pdf.ln(5)

                            pdf.set_text_color(32, 33, 36)
                        else:
                            pdf.set_font('Helvetica', '', 10)
                            pdf.cell(0, 5, "Storyboard frames could not be extracted.", 0, 1)

                # Narrative arc and other details
                if isinstance(metadata, dict):
                    pdf.ln(3)
                    pdf.set_font('Helvetica', '', 10)
                    pdf.set_text_color(32, 33, 36)

                    if metadata.get("narrative_arc"):
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.cell(0, 5, "Narrative Arc:", 0, 1)
                        pdf.set_font('Helvetica', '', 10)
                        pdf.multi_cell(0, 5, metadata["narrative_arc"], 0)
                        pdf.ln(2)

                    if metadata.get("target_audience_appeal"):
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.cell(0, 5, "Target Audience Appeal:", 0, 1)
                        pdf.set_font('Helvetica', '', 10)
                        pdf.multi_cell(0, 5, metadata["target_audience_appeal"], 0)

            # ==================== #
            # 6. FOCUS GROUP REPORT
            # ==================== #
            if focus_group_evaluation or panelists:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 18)
                pdf.set_text_color(0, 51, 160)
                pdf.cell(0, 10, "Focus Group Evaluation", 0, 1)
                pdf.ln(3)

                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(32, 33, 36)

                if focus_group_evaluation:
                    # Parse the evaluation text with table support
                    eval_lines = focus_group_evaluation.split('\n')
                    in_table = False
                    for line in eval_lines:
                        line_stripped = line.strip()

                        # Detect markdown tables (| col1 | col2 |)
                        if '|' in line_stripped and line_stripped.startswith('|'):
                            cells = [c.strip() for c in line_stripped.split('|') if c.strip()]
                            # Skip separator rows (|---|---|)
                            if all(set(c) <= {'-', ':'} for c in cells):
                                continue
                            if not in_table:
                                in_table = True
                                # Table header row
                                pdf.set_font('Helvetica', 'B', 9)
                                pdf.set_fill_color(0, 51, 160)
                                pdf.set_text_color(255, 255, 255)
                                col_w = 190 / max(len(cells), 1)
                                for cell in cells:
                                    pdf.cell(col_w, 6, cell[:30], 1, 0, 'C', True)
                                pdf.ln()
                                pdf.set_text_color(32, 33, 36)
                            else:
                                # Table body row
                                pdf.set_font('Helvetica', '', 8)
                                row_fill = pdf.page_no() % 2 == 0  # alternating is hard per-row, skip
                                col_w = 190 / max(len(cells), 1)
                                for cell in cells:
                                    pdf.cell(col_w, 5, cell[:30], 1, 0, 'L')
                                pdf.ln()
                        else:
                            if in_table:
                                in_table = False
                                pdf.ln(2)

                            if line_stripped.startswith('###'):
                                pdf.ln(2)
                                pdf.set_font('Helvetica', 'B', 11)
                                pdf.set_text_color(26, 115, 232)
                                pdf.multi_cell(0, 5, line_stripped.lstrip('#').strip(), 0)
                                pdf.set_font('Helvetica', '', 10)
                                pdf.set_text_color(32, 33, 36)
                            elif line_stripped.startswith('##'):
                                pdf.ln(2)
                                pdf.set_font('Helvetica', 'B', 12)
                                pdf.set_text_color(26, 115, 232)
                                pdf.multi_cell(0, 6, line_stripped.lstrip('#').strip(), 0)
                                pdf.set_font('Helvetica', '', 10)
                                pdf.set_text_color(32, 33, 36)
                            elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
                                pdf.set_x(15)
                                pdf.multi_cell(0, 5, f"• {line_stripped[2:]}", 0)
                            elif '**' in line_stripped:
                                # Bold text — render with emphasis
                                clean = line_stripped.replace('**', '')
                                if clean.strip():
                                    pdf.set_font('Helvetica', 'B', 10)
                                    pdf.multi_cell(0, 5, clean, 0)
                                    pdf.set_font('Helvetica', '', 10)
                            elif line_stripped:
                                pdf.multi_cell(0, 5, line_stripped, 0)
                            else:
                                pdf.ln(1)
                else:
                    pdf.multi_cell(0, 5, "No focus group evaluation was conducted.", 0)

                # Panelist profiles with portrait images
                if panelists:
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 18)
                    pdf.set_text_color(0, 51, 160)
                    pdf.cell(0, 10, "Focus Group Panelists", 0, 1)
                    pdf.ln(3)

                    PORTRAIT_DIR = f"{DIR}/portraits"
                    os.makedirs(PORTRAIT_DIR, exist_ok=True)

                    for p in panelists:
                        name = p.get("name", "Unknown")
                        age = p.get("age", "N/A")
                        persona = p.get("persona", "")
                        portrait_uri = p.get("portrait_gcs_uri", "")

                        # Try to download and embed portrait
                        portrait_local = None
                        if portrait_uri:
                            try:
                                safe_n = name.replace(" ", "_").replace(",", "")
                                portrait_local = os.path.join(PORTRAIT_DIR, f"{safe_n}.png")
                                blob_name = portrait_uri.replace(gcs_bucket + "/", "")
                                download_image_from_gcs(
                                    source_blob_name=blob_name,
                                    destination_file_name=portrait_local,
                                )
                            except Exception as e:
                                logging.warning(f"Could not download panelist portrait {name}: {e}")
                                portrait_local = None

                        # Card layout: portrait left, info right
                        card_y = pdf.get_y()
                        pdf.set_fill_color(248, 249, 250)
                        pdf.rect(10, card_y, 190, 55, 'F')

                        if portrait_local and os.path.exists(portrait_local):
                            try:
                                pdf.image(portrait_local, x=15, y=card_y + 5, w=40, h=40)
                            except Exception:
                                pass

                        info_x = 65 if portrait_local else 15
                        pdf.set_xy(info_x, card_y + 5)
                        pdf.set_font('Helvetica', 'B', 13)
                        pdf.set_text_color(32, 33, 36)
                        pdf.cell(0, 7, f"{name}, Age {age}", 0, 1)

                        pdf.set_x(info_x)
                        pdf.set_font('Helvetica', 'I', 10)
                        pdf.set_text_color(80, 80, 80)
                        if persona:
                            pdf.multi_cell(130, 5, persona[:200], 0)

                        if p.get("testimonial_video_gcs_uri"):
                            pdf.set_x(info_x)
                            pdf.set_font('Helvetica', '', 8)
                            pdf.set_text_color(26, 115, 232)
                            pdf.cell(0, 4, "Video testimonial recorded", 0, 1)

                        pdf.set_y(card_y + 60)
                        pdf.ln(3)

            # ==================== #
            # 7. BACK COVER
            # ==================== #
            pdf.is_back_cover = True
            pdf.add_page()

            # Bottom accent bar
            pdf.set_fill_color(0, 51, 160)
            pdf.rect(0, 267, 210, 30, 'F')

            # Center content
            pdf.set_y(100)
            pdf.set_font('Helvetica', 'B', 24)
            pdf.set_text_color(0, 51, 160)
            pdf.cell(0, 12, "Trends & Insights AI Platform", 0, 1, 'C')

            pdf.ln(10)
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "Powered by Google Gemini, Veo, and Agent Development Kit", 0, 1, 'C')

            pdf.ln(20)
            pdf.set_font('Helvetica', '', 10)

            # Campaign metadata summary
            summary_items = [
                f"Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                f"Total Images: {len(img_artifact_list or [])}",
                f"Total Videos: {len(vid_artifact_list or [])}",
                f"Commercial: {'Included' if has_commercial else 'Not produced'}",
                f"Focus Group: {focus_verdict}",
            ]

            for item in summary_items:
                pdf.cell(0, 6, item, 0, 1, 'C')

            pdf.is_back_cover = False

            # Output branded PDF
            pdf.output(report_filepath)

        except Exception as branded_err:
            logging.warning(f"Branded PDF layout failed ({branded_err}), falling back to simple PDF")
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font('Helvetica', '', 10)
            all_text = f"{processed_report}\n\n{IMG_CREATIVE_STRING}\n\n{VID_CREATIVE_STRING}\n\n{COMMERCIAL_STRING}\n\n{FOCUS_GROUP_STRING}"
            for line in all_text.split('\n'):
                safe_line = _sanitize_text(line.strip())
                if safe_line:
                    try:
                        pdf.multi_cell(0, 5, safe_line, 0)
                    except Exception:
                        pass
                else:
                    pdf.ln(2)
            pdf.output(report_filepath)

        with open(report_filepath, "rb") as f:
            document_bytes = f.read()

        document_part = types.Part(
            inline_data=types.Blob(data=document_bytes, mime_type="application/pdf")
        )

        version = None
        if save_artifact_fn:
            version = await save_artifact_fn(pdf_artifact_key, document_part)

        if gcs_folder:
            upload_blob_to_gcs(
                source_file_name=report_filepath,
                destination_blob_name=os.path.join(gcs_folder, pdf_artifact_key),
            )

        logging.info(
            f"\n\nSaved final report '{pdf_artifact_key}', version {version}, to folder '{gcs_folder}'\n\n"
        )

        shutil.rmtree(DIR)
        return {
            "status": "ok",
            "artifact_key": pdf_artifact_key,
            "version": version,
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
