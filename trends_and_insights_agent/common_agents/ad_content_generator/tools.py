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
from google.genai.types import GenerateVideosConfig

from ...shared_libraries.config import config
from ...shared_libraries.utils import (
    download_blob,
    upload_blob_to_gcs,
    download_image_from_gcs,
)

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
    f"""Generates an image based on the prompt for {config.image_gen_model}

    Args:
        prompt (str): The prompt to generate the image from.
        tool_context (ToolContext): The tool context.
        concept_name (str, optional): The name of the concept.
        number_of_images (int, optional): The number of images to generate. Defaults to 1.

    Returns:
        dict: Status and the artifact_key of the generated image.

    """
    response = client.models.generate_images(
        model=config.image_gen_model,
        prompt=prompt,
        config={"number_of_images": number_of_images},
    )
    if not response.generated_images:
        return {"status": "failed"}

    # Create output filename
    if concept_name:
        filename_prefix = f"{concept_name.replace(",", "").replace(" ", "_")}"
    else:
        filename_prefix = f"{str(uuid.uuid4())[:8]}"

    DIR = "session_media"
    SUBDIR = f"{DIR}/imgs"
    if not os.path.exists(SUBDIR):
        os.makedirs(SUBDIR)

    for index, image_results in enumerate(response.generated_images):
        if image_results.image is not None:
            if image_results.image.image_bytes is not None:

                image_bytes = image_results.image.image_bytes
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

    Args:
        prompt (str): The prompt to generate the video from.
        concept_name (str, optional): The name of the creative/visual concept.
        tool_context (ToolContext): The tool context.
        number_of_videos (int, optional): The number of videos to generate. Defaults to 1.
        negative_prompt (str, optional): The negative prompt to use. Defaults to "".

    Returns:
        dict: Status and the `artifact_key` of the generated video.
    """
    # Create output filename
    if concept_name:
        filename_prefix = f"{concept_name.replace(",", "").replace(" ", "_")}"
    else:
        filename_prefix = f"{str(uuid.uuid4())[:8]}"

    gen_config = GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=number_of_videos,
        output_gcs_uri=os.environ["BUCKET"],
        negative_prompt=negative_prompt,
    )
    if existing_image_filename != "":
        gcs_location = f"{os.environ['BUCKET']}/{existing_image_filename}"
        existing_image = types.Image(gcs_uri=gcs_location, mime_type="image/png")
        operation = client.models.generate_videos(
            model=config.video_gen_model,
            prompt=prompt,
            image=existing_image,
            config=gen_config,
        )
    else:
        operation = client.models.generate_videos(
            model=config.video_gen_model, prompt=prompt, config=gen_config
        )
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        logging.info(operation)

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
    Tool to save image artifact details to the session state.
    Use this tool after generating an image with the `generate_image` tool.

    Args:
        artifact_key_dict (dict): A dict representing a generated image artifact. Use the `tool_context` to extract the following schema:
            artifact_key (str): The filename used to identify the image artifact; the value returned in `generate_image` tool response.
            img_prompt (str): The prompt used to generate the image artifact.
            concept (str): A brief explanation of the creative concept used to generate this artifact.
            headline (str): The attention-grabbing headline proposed for the artifact's ad-copy.
            caption (str): The candidate social media caption proposed for the artifact's ad-copy.
            trend (str): The trend(s) referenced by this creative.
        tool_context (ToolContext) The tool context.

    Returns:
        dict: the status of this functions overall outcome.
    """
    existing_img_artifact_keys = tool_context.state.get("img_artifact_keys")
    if existing_img_artifact_keys is not {"img_artifact_keys": []}:
        existing_img_artifact_keys["img_artifact_keys"].append(artifact_key_dict)
    tool_context.state["img_artifact_keys"] = existing_img_artifact_keys
    return {"status": "ok"}


async def save_vid_artifact_key(
    artifact_key_dict: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Tool to save video artifact details to the session state.
    Use this tool after generating an video with the `generate_video` tool.

    Args:
        artifact_key_dict (dict): A dict representing a generated video artifact. Use the `tool_context` to extract the following schema:
            artifact_key (str): The filename used to identify the video artifact; the value returned in `generate_video` tool response.
            vid_prompt (str): The prompt used to generate the video artifact.
            concept (str): A brief explanation of the creative concept used to generate this artifact.
            headline (str): The attention-grabbing headline proposed for the artifact's ad-copy.
            caption (str): The candidate social media caption proposed for the artifact's ad-copy.
            trend (str): The trend(s) referenced by this creative.
        tool_context (ToolContext) The tool context.

    Returns:
        dict: the status of this functions overall outcome.
    """
    existing_vid_artifact_keys = tool_context.state.get("vid_artifact_keys")
    if existing_vid_artifact_keys is not {"vid_artifact_keys": []}:
        existing_vid_artifact_keys["vid_artifact_keys"].append(artifact_key_dict)
    tool_context.state["vid_artifact_keys"] = existing_vid_artifact_keys
    return {"status": "ok"}


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
    """
    Saves generated PDF report bytes as an artifact.

    Args:
        tool_context (ToolContext): The tool context.

    Returns:
        dict: Status and the location of the PDF artifact file.
    """
    processed_report = tool_context.state["final_report_with_citations"]
    gcs_folder = tool_context.state["gcs_folder"]

    try:

        DIR = f"report_creatives"

        # ==================== #
        # get image creatives
        # ==================== #
        IMG_SUBDIR = f"{DIR}/imgs"
        if not os.path.exists(IMG_SUBDIR):
            os.makedirs(IMG_SUBDIR)

        # get artifact details
        img_artifact_state_dict = tool_context.state.get("img_artifact_keys")
        img_artifact_list = img_artifact_state_dict["img_artifact_keys"]

        IMG_CREATIVE_STRING = ""
        for entry in img_artifact_list:
            logging.info(entry)
            LOCAL_FILE_PATH = os.path.join(IMG_SUBDIR, entry["artifact_key"])
            ARTIFACT_KEY_NAME = entry["artifact_key"].replace(".png", "")
            # download locally
            download_image_from_gcs(
                source_blob_name=os.path.join(gcs_folder, entry["artifact_key"]),
                destination_file_name=LOCAL_FILE_PATH,
            )
            # TODO: optimize
            path_str = f"![Example Image]({LOCAL_FILE_PATH})\n"
            str_1 = f"## {entry["headline"]}\n"
            str_2 = f"*{os.path.join(GCS_BUCKET, gcs_folder, entry["artifact_key"])}*\n\n"
            str_3 = f"{path_str}\n\n"
            str_4 = f"**{entry["caption"]}**\n\n"
            str_5 = f"**Trend(s):** {entry["trend"]}\n\n"
            str_6 = f"**Visual Concept:** {entry["concept"]}\n\n"
            str_7 = f"**Prompt:** {entry["img_prompt"]}\n\n"
            result = (
                str_1
                + " "
                + str_2
                + " "
                + str_3
                + " "
                + str_4
                + " "
                + str_5
                + " "
                + str_6
                + " "
                + str_7
            )

            IMG_CREATIVE_STRING += result

        # ==================== #
        # get video creatives
        # ==================== #
        VID_SUBDIR = f"{DIR}/vids"
        if not os.path.exists(VID_SUBDIR):
            os.makedirs(VID_SUBDIR)

        # get artifact details
        vid_artifact_state_dict = tool_context.state.get("vid_artifact_keys")
        vid_artifact_list = vid_artifact_state_dict["vid_artifact_keys"]

        VID_CREATIVE_STRING = ""
        for entry in vid_artifact_list:
            logging.info(entry)
            LOCAL_VID_PATH = os.path.join(VID_SUBDIR, entry["artifact_key"])
            ARTIFACT_KEY_NAME = entry["artifact_key"].replace(".mp4", "")
            # download locally
            download_image_from_gcs(
                source_blob_name=os.path.join(gcs_folder, entry["artifact_key"]),
                destination_file_name=LOCAL_VID_PATH,
            )
            LOCAL_FRAME_PATH = os.path.join(VID_SUBDIR, f"{ARTIFACT_KEY_NAME}.png")
            LOCAL_VID_FRAME = extract_single_frame(LOCAL_VID_PATH, 1, LOCAL_FRAME_PATH)

            path_str = f"![Thumbnail Image]({LOCAL_VID_FRAME})\n"
            str_1 = f"## {entry["headline"]}\n"
            str_2 = f"*{os.path.join(GCS_BUCKET, gcs_folder, entry["artifact_key"])}*\n\n"
            str_3 = f"{path_str}\n\n"
            str_4 = f"**{entry["caption"]}**\n\n"
            str_5 = f"**Trend(s):** {entry["trend"]}\n\n"
            str_6 = f"**Visual Concept:** {entry["concept"]}\n\n"
            str_7 = f"**Prompt:** {entry["vid_prompt"]}\n\n"

            result = (
                str_1
                + " "
                + str_2
                + " "
                + str_3
                + " "
                + str_4
                + " "
                + str_5
                + " "
                + str_6
                + " "
                + str_7
            )

            VID_CREATIVE_STRING += result

        # ==================== #
        # create local PDF file
        # ==================== #
        artifact_key = "final_trends_and_creatives_report.pdf"
        report_filepath = f"{DIR}/{artifact_key}"

        # create PDF object
        pdf = MarkdownPdf(toc_level=4)
        pdf.add_section(Section(f" {processed_report}\n"))
        pdf.add_section(
            Section(f"# Ad Creatives\n\n{IMG_CREATIVE_STRING}\n\n{VID_CREATIVE_STRING}")
        )
        pdf.meta["title"] = "[Final] trends-2-creatives Report"
        pdf.save(report_filepath)

        # open pdf and read bytes for types.Part() object
        with open(report_filepath, "rb") as f:
            document_bytes = f.read()

        # artifact build
        document_part = types.Part(
            inline_data=types.Blob(data=document_bytes, mime_type="application/pdf")
        )
        version = await tool_context.save_artifact(
            filename=artifact_key, artifact=document_part
        )
        logging.info(
            f"\n\nSaved report artifact: '{artifact_key}' as version {version}\n\n"
        )
        upload_blob_to_gcs(
            source_file_name=report_filepath,
            destination_blob_name=os.path.join(gcs_folder, artifact_key),
        )
        logging.info(
            f"\n\nSaved artifact doc '{artifact_key}', version {version}, to folder '{gcs_folder}'\n\n"
        )
        # clean up
        shutil.rmtree(DIR)
        logging.info(f"Directory '{DIR}' and its contents removed successfully")
        return {"status": "ok", "artifact_key": artifact_key}
    except Exception as e:
        logging.error(f"Error saving artifact: {e}")
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
