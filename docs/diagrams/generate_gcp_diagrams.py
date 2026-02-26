"""Generate 3 GCP-branded architecture diagrams for the Marketing Intelligence System.

Diagram 1: Cloud Run Deployment Architecture
Diagram 2: Agent Engine Deployment Architecture
Diagram 3: End-to-End Data Flow
"""

import os
import sys
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load env from the agent directory
load_dotenv(Path(__file__).parent.parent.parent / "trends_and_insights_agent" / ".env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "wortz-project-352116")
OUTPUT_DIR = Path(__file__).parent

# Model fallback chain
MODELS = [
    ("gemini-3-pro-image-preview", "global"),
    ("gemini-2.5-flash-image", "us-central1"),
]


def generate_diagram(prompt: str, output_path: Path) -> bool:
    """Generate a diagram using Gemini image generation with fallback."""
    for model, location in MODELS:
        try:
            print(f"  Trying {model} ({location})...")
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=location)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    with open(output_path, "wb") as f:
                        f.write(part.inline_data.data)
                    print(f"  Saved to {output_path}")
                    return True
            print(f"  No image data in response from {model}")
        except Exception as e:
            print(f"  {model} failed: {e}")
            continue
    return False


# ============================================================
# DIAGRAM 1: Cloud Run Deployment Architecture
# ============================================================
PROMPT_CLOUD_RUN = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.
Google Cloud product icon style, clean lines, no 3D effects, modern flat design.

Title: "Cloud Run Deployment Architecture"
Subtitle: "Marketing Intelligence Multi-Agent System"

Layout the diagram in LANDSCAPE orientation with these zones from left to right:

LEFT ZONE - "Client Layer":
  - "User Browser" box with a browser icon
  - Contains "React Frontend (ADK Web UI)" label
  - Arrow labeled "HTTPS" going right

CENTER ZONE - "Google Cloud Run" (large blue container #4285F4):
  - Service: "trends-and-insights-frontend"
  - Inside the Cloud Run container, show FOUR processes managed by supervisord:
    - "nginx" (reverse proxy, port 8080):
      - Routes / to React static files
      - Routes /api/ to API server (port 8000)
      - Routes /adk/ to ADK server (port 8001)
      - Routes /ws/ to Voice WebSocket (port 8081)
    - "API Server" (FastAPI, port 8000):
      - REST endpoints for frontend
    - "ADK Server" (port 8001):
      - "root_agent" orchestrator
      - 5 sub-agents: trends, research, ad creative, av studio, focus group
    - "Voice Server" (WebSocket, port 8081):
      - Gemini Live API streaming
      - PCM audio via AudioWorklet

  SECOND Cloud Run Service: "trends-and-insights-a2a" (separate blue container):
    - A2A protocol endpoint (port 8080)
    - Serves /.well-known/agent.json
    - JSON-RPC/SSE transport
    - Arrow from "Gemini Enterprise / Discovery Engine" to this service

RIGHT ZONE - "GCP Services" column, each in its own box with appropriate color:
  1. "Vertex AI" (purple #A142F4) containing sub-items:
     - Gemini 3 Flash Preview (LLM)
     - Gemini 3 Pro Image Preview
     - Imagen 4.0 Ultra (image gen)
     - Veo 3.1 Fast (video gen)
     - Lyria (music gen)
     - Chirp 3 HD (voice/TTS)
  2. "Cloud Storage (GCS)" (yellow #FBBC05):
     - Media artifacts bucket
     - Images, video clips, commercials
  3. "Secret Manager" (red #EA4335):
     - YouTube API key
     - API credentials
  4. "BigQuery" (blue #4285F4):
     - Google Trends data
     - Analytics

TOP RIGHT - "Gemini Enterprise / Discovery Engine":
  - Arrow labeled "A2A discovery" to trends-and-insights-a2a service
  - Arrow labeled "/.well-known/agent.json" from A2A service back

BOTTOM - "External APIs":
  - "YouTube Data API v3" (red box)
  - "Google Search" (blue box)

Show arrows connecting:
  - Cloud Run ADK server to Vertex AI models
  - Cloud Run to GCS for artifact storage
  - Cloud Run to Secret Manager for credentials
  - trends_and_insights_agent to BigQuery
  - trends_and_insights_agent to YouTube Data API
  - research_orchestrator to Google Search
  - Gemini Enterprise to A2A service

Add a "Cloud IAM" label at the top right corner.
Add "Cloud Logging" and "Cloud Trace" labels at bottom of Cloud Run.

Clean flat design. Google Cloud logo watermark at bottom left.
Leave blank square placeholders where GCP product icons would go.
"""

# ============================================================
# DIAGRAM 2: Agent Engine Deployment Architecture
# ============================================================
PROMPT_AGENT_ENGINE = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.
Google Cloud product icon style, clean lines, no 3D effects, modern flat design.

Title: "Agent Engine Deployment Architecture"
Subtitle: "Vertex AI Agent Engine with Memory Bank"

Layout in LANDSCAPE orientation with these zones:

TOP - "Client Applications" row:
  - "Agentspace" box (blue #4285F4)
  - "Custom Client" box (gray #5F6368)
  - "ADK Web UI" box (green #34A853)
  - All connect down via "Agent Engine API" arrows

CENTER-LEFT - "Vertex AI Agent Engine" (large purple container #A142F4):
  - Display name: "trends-and-insights-2026-02-25"
  - Inside, show the agent hierarchy as a tree:
    - "root_agent" (blue orchestrator box) at top
    - Below root, 5 sub-agents in a row:
      1. "trends_and_insights_agent" (green #34A853) - "Trend Discovery"
      2. "research_orchestrator" (blue #4285F4) - "Market Research"
      3. "ad_content_generator_agent" (purple #A142F4) - "Ad Creative"
      4. "av_editing_studio_agent" (teal #12B5CB) - "AV Studio"
      5. "focus_group_evaluator_agent" (orange #F29900) - "Focus Group"
    - Under research_orchestrator, show nested agents:
      - "parallel_planner_agent" containing:
        - yt_sequential_planner
        - gs_sequential_planner
        - ca_sequential_planner
      - merge_planners -> combined_web_evaluator -> enhanced_combined_searcher -> combined_report_composer
    - Under ad_content_generator_agent, show:
      - ad_creative_pipeline (drafter -> critic)
      - visual_generation_pipeline (drafter -> critic -> finalizer)
      - visual_generator

  - "Session Management" box inside Agent Engine
  - "Tracing & Telemetry" box (OTEL enabled)

CENTER-RIGHT - "Memory & Storage" column:
  1. "Vertex AI Memory Bank" (purple box #A142F4):
     - "VertexAiMemoryBankService"
     - "preload_memory tool"
     - Arrow from root_agent to Memory Bank labeled "memorize / recall"
  2. "Cloud Storage (GCS)" (yellow #FBBC05):
     - "Staging bucket" for deployment packages
     - "Artifacts bucket" for media outputs
     - Arrows from av_editing_studio_agent and ad_content_generator_agent

BOTTOM - "Vertex AI Model Endpoints" (wide purple bar):
  Row of model boxes:
  - "Gemini 3 Flash Preview" - all LLM agents
  - "Gemini 3 Pro Image Preview" - subject reference images
  - "Imagen 4.0 Ultra" - ad creative images
  - "Veo 3.1 Fast" - video clips
  - "Lyria" - music soundtrack
  - "Chirp 3 HD" - voice-over

RIGHT SIDE - "Supporting Services":
  - "Secret Manager" (red #EA4335): YT API key, env vars
  - "Cloud Build" (blue #4285F4): custom install scripts (ffmpeg, opencv)
  - "BigQuery" (blue #4285F4): Google Trends data

Show deployment flow: deploy_to_ae.py -> AdkApp -> agent_engines.create()
Show build_options: install_opencv.sh, install_ffmpeg.sh

Clean flat design. Google Cloud logo watermark at bottom left.
Leave blank square placeholders where GCP product icons would go.
"""

# ============================================================
# DIAGRAM 3: End-to-End Data Flow
# ============================================================
PROMPT_DATA_FLOW = """
Generate a professional data flow diagram in Google Cloud Platform
documentation style. Clean white background, GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335). No 3D effects, modern flat design.

Title: "End-to-End Data Flow"
Subtitle: "From User Input to 30-Second Commercial"

Show a top-to-bottom flow with numbered phases and color-coded skill sections:

PHASE 1: "User Input" (red ellipse #EA4335 at top):
  - Brand brief / PDF upload / campaign prompt
  - Arrow down to root_agent

PHASE 2: "Campaign Setup & Trend Discovery" (green section #34A853):
  - "trends_and_insights_agent"
  - Left input: "BigQuery" -> "Google Trends data (top 20 daily)"
  - Right input: "YouTube Data API" -> "Trending videos (top 45)"
  - Outputs (green arrows to session state bar):
    - brand, target_product, target_audience
    - key_selling_points
    - target_search_trends, target_yt_trends
  - User selects trends interactively

PHASE 3: "Parallel Market Research" (blue section #4285F4):
  - Show 3 parallel lanes running simultaneously:
    - Lane 1: "YouTube Research" - yt_analysis -> yt_web_planner -> yt_web_searcher
    - Lane 2: "Google Search Research" - gs_web_planner -> gs_web_searcher
    - Lane 3: "Campaign Research" - campaign_web_planner -> campaign_web_searcher
  - Merge arrow: "merge_planners" combines all 3 lanes
  - Sequential flow: combined_web_evaluator -> enhanced_combined_searcher -> combined_report_composer
  - External: "Google Search (grounding)" service
  - Output: "combined_final_cited_report" with citation tracking

PHASE 4: "Ad Creative Generation" (purple section #A142F4):
  - Two parallel pipelines:
    - Pipeline A: "Ad Copy" - ad_copy_drafter -> ad_copy_critic -> user selects 6-8 copies
    - Pipeline B: "Visual Concepts" - visual_concept_drafter -> visual_concept_critic -> visual_concept_finalizer -> user selects concepts
  - Then: visual_generator produces assets
  - External services: "Imagen 4.0 Ultra" (images), "Veo 3.1 Fast" (videos)
  - Output: final_select_ad_copies, final_select_vis_concepts, generated images/videos

PHASE 5: "AV Production" (teal section #12B5CB):
  - Show a production pipeline with 4 tracks:
    - Track 1 "Video": generate_subject_image -> generate_clip_with_frames -> concatenate_clips -> trim_video
    - Track 2 "Music": recommend_audio_style -> generate_commercial_soundtrack -> generate_sound_effects
    - Track 3 "Voice": generate_voice_over -> generate_dialogue -> generate_branded_tagline
    - Track 4 "Assembly": combine_audio_with_video -> mix_voice_with_audio -> save_commercial_artifact
  - External: "Gemini 3 Pro Image" (reference), "Veo 3.1" (clips), "Lyria" (music), "Chirp 3 HD" (voice)
  - ffmpeg for concatenation and mixing

PHASE 6: "Focus Group Evaluation" (orange section #F29900):
  - "focus_group_evaluator_agent"
  - Input: commercial_artifact from GCS
  - analyze_commercial_video tool with Gemini vision
  - Output: quality score, consistency rating, trend relevance, audience uplift

PHASE 7: "Final Output" (red ellipse #EA4335 at bottom):
  - 30-second commercial video (GCS)
  - Cited research report (PDF)
  - Ad copy collection
  - Visual concept gallery
  - Focus group evaluation report

RIGHT SIDE: "Session State" (yellow vertical bar #FBBC05):
  Running alongside all phases, showing key state variables being read/written
  by each phase with arrows.

LEFT SIDE: "GCS Artifacts" (yellow vertical bar #FBBC05):
  Showing artifacts being stored at each phase:
  - Images, video clips, audio tracks
  - Final commercial
  - Research report PDF

Clean flowchart style. Google Cloud logo watermark at bottom left.
Leave blank square placeholders where GCP product icons would go.
"""


def main():
    diagrams = [
        ("Diagram 1: Cloud Run Deployment Architecture", PROMPT_CLOUD_RUN, OUTPUT_DIR / "cloud_run_architecture.png"),
        ("Diagram 2: Agent Engine Deployment Architecture", PROMPT_AGENT_ENGINE, OUTPUT_DIR / "agent_engine_architecture.png"),
        ("Diagram 3: End-to-End Data Flow", PROMPT_DATA_FLOW, OUTPUT_DIR / "e2e_data_flow.png"),
    ]

    results = []
    for title, prompt, output_path in diagrams:
        print(f"\nGenerating {title}...")
        success = generate_diagram(prompt, output_path)
        results.append((title, success, output_path))

    print("\n" + "=" * 60)
    print("RESULTS:")
    for title, success, path in results:
        status = "OK" if success else "FAILED"
        print(f"  [{status}] {title} -> {path}")


if __name__ == "__main__":
    main()
