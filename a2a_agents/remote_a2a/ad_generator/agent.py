"""Ad Content Generator A2A Server Agent.

This agent generates comprehensive ad campaigns including copy, visual concepts,
and actual image/video generation using Imagen and Veo models.
"""

import logging
from typing import List, Dict
from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search, load_artifacts, ToolContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config
from .config import config


def generate_image(
    prompt: str,
    tool_context: ToolContext,
    number_of_images: int = 1,
    aspect_ratio: str = "1:1",
) -> dict:
    """
    Mock image generation for a2a demo.
    
    Args:
        prompt: The image generation prompt.
        tool_context: The ADK tool context.
        number_of_images: Number of images to generate.
        aspect_ratio: Aspect ratio for the images.
    
    Returns:
        Status and mock image URLs.
    """
    # Mock image generation
    images = []
    for i in range(number_of_images):
        image_url = f"https://example.com/generated_image_{i+1}.jpg"
        images.append(image_url)
    
    # Save to session state
    img_keys = tool_context.state.get("img_artifact_keys", {"img_artifact_keys": []})
    img_keys["img_artifact_keys"].extend(images)
    tool_context.state["img_artifact_keys"] = img_keys
    
    return {
        "status": "Images generated successfully",
        "images": images,
        "prompt_used": prompt,
    }


def generate_video(
    prompt: str,
    tool_context: ToolContext,
    duration: int = 8,
    aspect_ratio: str = "16:9",
) -> dict:
    """
    Mock video generation for a2a demo.
    
    Args:
        prompt: The video generation prompt.
        tool_context: The ADK tool context.
        duration: Video duration in seconds.
        aspect_ratio: Aspect ratio for the video.
    
    Returns:
        Status and mock video URL.
    """
    # Mock video generation
    video_url = f"https://example.com/generated_video.mp4"
    
    # Save to session state
    vid_keys = tool_context.state.get("vid_artifact_keys", {"vid_artifact_keys": []})
    vid_keys["vid_artifact_keys"].append(video_url)
    tool_context.state["vid_artifact_keys"] = vid_keys
    
    return {
        "status": "Video generated successfully",
        "video": video_url,
        "prompt_used": prompt,
        "duration": duration,
    }


def save_select_ad_copy(
    selected_ad_copies: List[Dict], tool_context: ToolContext
) -> dict:
    """
    Save selected ad copies to session state.
    
    Args:
        selected_ad_copies: List of selected ad copy dictionaries.
        tool_context: The ADK tool context.
    
    Returns:
        Status message.
    """
    tool_context.state["final_select_ad_copies"] = {"final_select_ad_copies": selected_ad_copies}
    return {"status": f"Saved {len(selected_ad_copies)} ad copies"}


def save_select_visual_concept(
    selected_concepts: List[Dict], tool_context: ToolContext
) -> dict:
    """
    Save selected visual concepts to session state.
    
    Args:
        selected_concepts: List of selected visual concept dictionaries.
        tool_context: The ADK tool context.
    
    Returns:
        Status message.
    """
    tool_context.state["final_select_vis_concepts"] = {"final_select_vis_concepts": selected_concepts}
    return {"status": f"Saved {len(selected_concepts)} visual concepts"}


def save_img_artifact_key(key: str, tool_context: ToolContext) -> dict:
    """Save image artifact key to session state."""
    img_keys = tool_context.state.get("img_artifact_keys", {"img_artifact_keys": []})
    img_keys["img_artifact_keys"].append(key)
    tool_context.state["img_artifact_keys"] = img_keys
    return {"status": "Image key saved"}


def save_vid_artifact_key(key: str, tool_context: ToolContext) -> dict:
    """Save video artifact key to session state."""
    vid_keys = tool_context.state.get("vid_artifact_keys", {"vid_artifact_keys": []})
    vid_keys["vid_artifact_keys"].append(key)
    tool_context.state["vid_artifact_keys"] = vid_keys
    return {"status": "Video key saved"}


# Ad generator instruction
AD_GENERATOR_INSTR = """You are an ad content generator that creates comprehensive ad campaigns.

Your main responsibilities:
1. Generate creative ad copy based on research insights
2. Develop visual concepts for the ad campaigns
3. Create images and videos using generation tools
4. Compile a complete creative package

Workflow:
1. Review the session state for:
   - draft_report: Research findings from the research orchestrator
   - target_product: The product being marketed
   - target_audience: The target audience
   - target_search_trends: Selected Google Search trends
   - target_yt_trends: Selected YouTube trends
   - campaign_guide_data: Campaign guidelines

2. Generate Ad Copy:
   - Create 6-8 ad copy variations
   - Each should include: headline, body text, call-to-action
   - Reference the trends authentically
   - Vary tone and approach
   - Use `save_select_ad_copy` to save the best options

3. Develop Visual Concepts:
   - Create visual concepts for each ad copy
   - Mix of image and video concepts
   - Describe each concept clearly
   - Consider platform requirements
   - Use `save_select_visual_concept` to save the concepts

4. Generate Visual Assets:
   - Use `generate_image` for image concepts
   - Use `generate_video` for video concepts
   - Create compelling prompts based on the concepts
   - Save artifact keys using the save functions

5. Use `google_search` to research:
   - Visual trends in advertising
   - Competitor campaigns
   - Best practices for the target audience

Be creative, culturally relevant, and ensure all content aligns with the campaign strategy."""


# Create root_agent for a2a protocol
root_agent = Agent(
    model=config.lite_planner_model,
    name="ad_content_generator_agent",
    description="Help users with ad generation; brainstorm and refine ad copy and visual concept ideas; generate final ad creatives.",
    instruction=AD_GENERATOR_INSTR,
    tools=[
        google_search,
        generate_image,
        generate_video,
        save_img_artifact_key,
        save_vid_artifact_key,
        save_select_ad_copy,
        save_select_visual_concept,
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)