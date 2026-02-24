"""Generate 3 GCP-branded architecture diagrams for the Skills-Based Agent Architecture."""

import sys
from pathlib import Path
from google import genai
from google.genai import types

PROJECT_ID = "wortz-project-352116"
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
# DIAGRAM 1: Skills-Based Agent Architecture
# ============================================================
PROMPT_1 = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.
Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.

Title: "Skills-Based Agent Architecture"
Subtitle: "Multi-Agent Marketing Intelligence System"

Show a hierarchical agent architecture with skill-based modular organization:

TOP: "User Query" (red ellipse, #EA4335)

CENTER: "root_agent" (large blue box #4285F4, labeled "Root Orchestrator"):
- Model: Gemini 3 Flash Preview
- Tools: save_creatives_and_research_report, preload_memory
- Planner: BuiltInPlanner with thinking

4 SKILL BRANCHES below the root agent, each in a rounded-corner container
with its own color and team label:

SKILL 1: "trend-discovery" (green container #34A853, team label "Data/Analytics Team"):
  - Agent: "trends_and_insights_agent" (green box)
  - Tools listed inside: memorize, get_daily_gtrends, get_youtube_trends
  - External services: BigQuery (orange box), YouTube Data API (red box)

SKILL 2: "market-research" (blue container #4285F4, team label "Research/Content Team"):
  - Agent: "research_orchestrator" (blue box) containing:
    - "parallel_planner_agent" running 3 sub-planners simultaneously:
      - yt_sequential_planner
      - gs_sequential_planner
      - ca_sequential_planner
    - merge_planners
    - combined_web_evaluator
    - enhanced_combined_searcher
    - combined_report_composer
  - External service: Google Search (blue box)

SKILL 3: "ad-creative" (purple container #A142F4, team label "Creative Team"):
  - Agent: "ad_content_generator_agent" (purple box) containing:
    - ad_creative_pipeline (drafter -> critic -> finalizer)
    - visual_generation_pipeline (drafter -> critic -> finalizer)
    - visual_generator
  - External services: Imagen 4.0 (purple box), Veo 3.1 (purple box)

SKILL 4: "av-studio" (teal container #12B5CB, team label "AV Production Team"):
  - Agent: "av_editing_studio_agent" (teal box)
  - Tools: generate_subject_image, generate_clip_with_frames, extract_frame_from_clip,
    concatenate_clips (ffmpeg), trim_video
  - External services: Gemini 3 Pro Image (teal box), Veo 3.1 (teal box)

FOUNDATION LAYER at the bottom spanning full width:
"shared_libraries" (gray container #5F6368):
  - config | callbacks | schema_types | utils | secrets

RIGHT SIDE: GCP Services column:
  - Vertex AI (purple box with icon placeholder)
  - Cloud Storage / GCS (yellow box with icon placeholder)
  - Secret Manager (red box with icon placeholder)
  - BigQuery (orange box with icon placeholder)

Show transfer_to_agent arrows (bold) between root and each skill's top agent.
Show connections from skills to GCP services on the right.

Clean flat design. Landscape orientation. Google Cloud logo watermark at bottom left.
Leave a blank square placeholder where each GCP product icon would go.
"""

# ============================================================
# DIAGRAM 2: Data Flow & Session State
# ============================================================
PROMPT_2 = """
Generate a professional data flow diagram in Google Cloud Platform
documentation style. Clean white background, GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335). No 3D effects, no hexagons,
modern flat design.

Title: "Data Flow & Session State Contract"
Subtitle: "From User Input Through Skills to Creative Output"

Show a top-to-bottom flow with numbered steps and session state passing:

Step 1: "User Query" (red ellipse at top, #EA4335)
- User provides: brand brief, PDF upload, or prompt

Step 2: "root_agent" (blue box #4285F4)
- Callbacks: _load_session_state, campaign_callback, rate_limit_callback
- Routes to appropriate skill

Step 3: "trend-discovery" (green box #34A853):
- WRITES to session state (green arrows):
  - brand, target_product, target_audience, key_selling_points
  - target_search_trends, target_yt_trends
- External: BigQuery (Google Trends data), YouTube Data API

Step 4: "market-research" (blue box #4285F4):
- READS (dashed arrows): brand, target_product, target_audience, target_search_trends, target_yt_trends
- Internal state: yt_video_analysis, combined_web_search_insights, sources, url_to_short_id
- WRITES: combined_final_cited_report, final_report_with_citations
- Callback: collect_research_sources_callback, citation_replacement_callback
- External: Google Search (with grounding)

Step 5: "ad-creative" (purple box #A142F4):
- READS: brand, target_product, target_audience, key_selling_points,
  target_search_trends, target_yt_trends, final_report_with_citations
- Internal state: ad_copy_draft, ad_copy_critique, visual_draft, visual_concept_critique
- WRITES: final_select_ad_copies, final_select_vis_concepts, img_artifact_keys, vid_artifact_keys
- External: Imagen 4.0 Ultra, Veo 3.1

Step 6: "av-studio" (teal box #12B5CB):
- READS: brand, target_product, final_select_ad_copies, final_select_vis_concepts
- WRITES: commercial_artifact
- External: Gemini 3 Pro Image, Veo 3.1, ffmpeg

Step 7: "Output" (red ellipse at bottom):
- 30-second commercial video
- Research report with citations
- Ad copy and visual concepts

Show session state as a horizontal yellow bar (#FBBC05) running alongside all skills,
with read/write arrows connecting each skill to the state keys they own.

On the right side, show the AI model integrations:
- Gemini 3 Flash Preview (all LLM agents)
- Imagen 4.0 Ultra (image generation)
- Veo 3.1 (video generation)
- Gemini 3 Pro Image (subject reference images)

Shared state key: gcs_folder (written by callbacks, read by all)

Clean flowchart style with color-coded skill sections. Google Cloud aesthetic.
Google Cloud logo watermark at bottom left.
Leave blank square placeholders where GCP product icons would go.
"""

# ============================================================
# DIAGRAM 3: Team Ownership & Development Model
# ============================================================
PROMPT_3 = """
Generate a professional architecture diagram in Google Cloud Platform
documentation style. Clean white background, GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335). No 3D effects, no hexagons,
modern flat design.

Title: "Team Ownership & Development Model"
Subtitle: "Independent Skill Development with Shared Contract Layer"

Show a diagram with 4 team ownership domains and shared infrastructure:

TOP ROW - 4 Team Boxes side by side, each with team name and ownership:

Team 1: "Data/Analytics Team" (green container #34A853):
  - Owns: trend-discovery skill (v1.0.0)
  - Files: agents.py, tools.py, prompts.py, SKILL.md
  - References: trend_selection_guide.md
  - Session keys owned: brand, target_product, target_audience,
    key_selling_points, target_search_trends, target_yt_trends

Team 2: "Research/Content Team" (blue container #4285F4):
  - Owns: market-research skill (v1.0.0)
  - Files: agents.py, tools.py, prompts.py, SKILL.md
  - Sub-agents: campaign, search, youtube web researchers
  - References: citation_system.md
  - Session keys owned: combined_final_cited_report, final_report_with_citations, sources

Team 3: "Creative Team" (purple container #A142F4):
  - Owns: ad-creative skill (v1.0.0)
  - Files: agents.py, tools.py, prompts.py, SKILL.md
  - References: veo3_prompting_guide.md
  - Session keys owned: final_select_ad_copies, final_select_vis_concepts,
    img_artifact_keys, vid_artifact_keys

Team 4: "AV Production Team" (teal container #12B5CB):
  - Owns: av-studio skill (v1.0.0)
  - Files: agents.py, tools.py, prompts.py, SKILL.md
  - References: storyboard_template.md
  - Session keys owned: commercial_artifact

MIDDLE LAYER - "Shared Contract Layer" (gray bar #5F6368):
  - shared_libraries/ (config, callbacks, schema_types, utils, secrets)
  - "Changes require cross-team review"
  - Session State Contract (shows key ownership boundaries)
  - SKILL.md as the interface contract

BOTTOM ROW - GCP Infrastructure:
  - Vertex AI (purple box): Gemini 3 Flash, Imagen 4.0, Veo 3.1
  - Cloud Storage (yellow box): GCS artifacts bucket
  - Secret Manager (red box): API keys
  - BigQuery (orange box): Google Trends data

Show arrows from each team's skill down through the shared contract layer to
the GCP infrastructure. Show that teams work independently within their skill
directory but share the contract layer.

Add a legend showing:
  - Solid arrows: "Direct dependency"
  - Dashed arrows: "Session state read"
  - Bold border: "Skill boundary (independent development)"

Clean flat design. Landscape orientation. Google Cloud logo watermark at bottom left.
Leave blank square placeholders where GCP product icons would go.
"""


def main():
    diagrams = [
        ("Diagram 1: Skills-Based Agent Architecture", PROMPT_1, OUTPUT_DIR / "skills_agent_architecture.png"),
        ("Diagram 2: Data Flow & Session State", PROMPT_2, OUTPUT_DIR / "data_flow_session_state.png"),
        ("Diagram 3: Team Ownership & Development Model", PROMPT_3, OUTPUT_DIR / "team_ownership_model.png"),
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
