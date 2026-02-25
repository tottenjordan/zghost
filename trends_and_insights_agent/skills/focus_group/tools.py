import logging
import os

from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from ...shared_libraries.config import config

logging.basicConfig(level=logging.INFO)

client = genai.Client()


def analyze_commercial_video(tool_context: ToolContext) -> dict:
    """Analyzes the 30-second commercial video using Gemini video understanding.

    Reads the commercial_artifact GCS URI from session state and sends
    the video to Gemini for detailed visual analysis including frame-by-frame
    description, character consistency, scene transitions, and production quality.

    Returns:
        dict with status and detailed analysis text.
    """
    commercial_artifact = tool_context.state.get("commercial_artifact")
    if not commercial_artifact:
        return {
            "status": "failed",
            "error": "No commercial_artifact found in session state. "
            "The commercial must be produced before running focus group evaluation.",
        }

    gcs_uri = commercial_artifact.get("gcs_uri", "")
    if not gcs_uri:
        return {
            "status": "failed",
            "error": "commercial_artifact has no gcs_uri.",
        }

    try:
        video = types.Part.from_uri(
            file_uri=gcs_uri,
            mime_type="video/mp4",
        )

        analysis_prompt = """You are a professional video production analyst. Analyze this 30-second commercial video in detail:

1. **Frame-by-Frame Visual Description**: Describe what happens in each major scene/shot transition. Note camera angles, movements, and compositions.

2. **Character Consistency Assessment**: Evaluate whether characters maintain consistent appearance (clothing, hair, features) across all scenes. Note any inconsistencies.

3. **Scene Transition Quality**: Rate the smoothness of transitions between scenes. Are they jarring or seamless? Do the visual elements flow naturally from one scene to the next?

4. **Visual Quality and Production Value**: Assess the overall visual fidelity - lighting, color grading, resolution, and any artifacts or quality issues.

5. **Product Visibility and Placement**: Identify where and how the product appears. Is it naturally integrated or forced? Is the brand clearly visible?

Provide your analysis in a structured format with clear sections for each category above."""

        contents = types.Content(
            role="user",
            parts=[types.Part.from_text(text=analysis_prompt), video],
        )

        result = client.models.generate_content(
            model=config.video_analysis_model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1),
        )

        if result and result.text:
            return {"status": "ok", "analysis": result.text}
        else:
            return {
                "status": "failed",
                "error": "Gemini returned empty analysis for the video.",
            }

    except Exception as e:
        logging.error(f"Failed to analyze commercial video: {e}")
        return {"status": "failed", "error": str(e)}
