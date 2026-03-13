# Trends & Insights — Capability Overview

> A multi-agent marketing intelligence system powered by Google ADK and Gemini that transforms real-time cultural trends into broadcast-ready advertising campaigns — from research to finished commercial — in under 25 minutes.

## Platform Summary

Trends & Insights is an AI-powered marketing platform that monitors what consumers care about right now, conducts deep market research around those signals, writes ad copy, generates images and video, produces full commercials with professional audio, and evaluates the result through a simulated focus group — all orchestrated by a hierarchy of specialized AI agents working in concert. The system runs on Google Cloud and is deployable to Vertex AI Agent Engine for enterprise use.

---

## 1. Trend Discovery

**Agent:** `trends_and_insights_agent`
**Model:** Gemini 3 Flash Preview

### What It Does

Surfaces the most relevant cultural signals from Google Search and YouTube in real time, then captures which trends a marketing team wants to target for their campaign. This is the starting point for every campaign — grounding all downstream creative in what audiences actually care about today.

### How It Works

- Queries the BigQuery public dataset `google_trends.top_terms` for the top 25 Google Search trends by rank and recency
- Calls the YouTube Data API to retrieve the most popular videos by region (default: US, up to 45 results)
- Presents both trend sets to the user as formatted tables for selection
- Saves selected Google Search trends and YouTube videos to session state for use by all downstream agents
- Stores campaign metadata (brand, product, audience, selling points) via a key-value memory tool

### Key Tools

| Tool | Purpose |
|------|---------|
| `get_daily_gtrends` | Retrieves the top 25 Google Search trends from BigQuery |
| `get_youtube_trends` | Fetches trending YouTube videos via the Data API |
| `save_search_trends_to_session_state` | Records selected Google Search trends |
| `save_yt_trends_to_session_state` | Records selected YouTube videos |
| `memorize` | Stores campaign metadata (brand, product, audience) |

### Business Value

Eliminates guesswork in trend identification. Every campaign starts with data-backed cultural signals, ensuring creative work is relevant to what audiences are searching for and watching right now.

---

## 2. Market Research

**Agent:** `research_orchestrator` (SequentialAgent)
**Models:** Gemini 3 Flash Preview (worker & critic roles)

### What It Does

Conducts multi-source market research across the selected Google Search trends, YouTube trends, and campaign brief simultaneously, then synthesizes findings into a professional cited report — replacing what would take a research team days.

### How It Works

- **Parallel research phase:** Three specialized research pipelines run concurrently:
  - YouTube trend analysis: analyzes trending videos, plans web research, executes searches
  - Google Search trend analysis: plans and executes web research around the selected search trend
  - Campaign research: investigates the product, audience, and competitive landscape
- **Merge phase:** Combines all three research streams into a unified summary
- **Quality evaluation:** A critic agent reviews the merged research for gaps, then generates 5-7 follow-up queries
- **Memory recall:** Retrieves prior campaign insights from Memory Bank (Vertex AI Agent Engine) to enrich the analysis
- **Enhanced search:** Executes follow-up queries via Google Search grounding, integrating new findings with prior insights
- **Report composition:** Generates a polished, in-line cited report organized by Campaign Guide, Search Trend, YouTube Trend, and Key Insights
- **Artifact save:** Exports the report as a PDF artifact to Google Cloud Storage

### Key Tools

| Tool | Purpose |
|------|---------|
| `google_search` | Google Search grounding for real-time web research |
| `recall_prior_insights` | Retrieves historical campaign learnings from Memory Bank |
| `save_draft_report_artifact` | Saves the cited report as a PDF artifact |

### Business Value

Delivers comprehensive, cited market research in minutes instead of days. The parallel pipeline and iterative quality checks ensure depth and accuracy, while Memory Bank integration means the system gets smarter with every campaign.

---

## 3. Ad Creative Generation

**Agent:** `ad_content_generator_agent`
**Models:** Gemini 3 Flash Preview (copy & visuals), Gemini 3 Pro Image Preview (image generation), Veo 3.1 Fast (video generation)

### What It Does

Takes the research report and selected trends, then produces a complete set of ad creatives — headlines, body copy, social captions, keyframe images, and short-form videos — through a structured draft-critique-finalize workflow that mirrors how a creative agency operates.

### How It Works

- **Phase 1 — Ad Copy (Draft-Critique):**
  - A creative copywriter agent drafts 10-12 ad copy ideas informed by trends, research, and campaign goals
  - A strategic marketing critic narrows them to the 6-8 strongest based on trend alignment, audience fit, and platform suitability
  - The orchestrator selects the top 2 and saves them to session state

- **Phase 2 — Visual Concepts (Draft-Critique-Finalize):**
  - A visual creative director drafts concepts for each ad copy, balancing image and video formats
  - A critic evaluates visual appeal, stopping power, and prompt quality
  - A finalizer locks in the top 2 concepts with polished image and video prompts

- **Phase 3 — Asset Generation (Image-to-Video Reference Workflow):**
  - For each concept: generates a keyframe image first, then passes it as a reference image to the video generator
  - This reference image workflow ensures visual continuity between the still and the motion asset
  - Runs Gecko fidelity evaluation to score product representation accuracy (0.0-1.0)
  - Saves all metadata (headline, caption, rationale, prompts) alongside each artifact

### Key Tools

| Tool | Purpose |
|------|---------|
| `generate_image` | Creates images via Gemini 3 Pro native image generation |
| `generate_video` | Produces 8-second videos via Veo 3.1 with optional reference image |
| `evaluate_media_fidelity` | Scores generated media against product description using Gecko |
| `save_select_ad_copy` | Saves selected ad copies to session state |
| `save_select_visual_concept` | Saves selected visual concepts to session state |
| `save_img_artifact_key` / `save_vid_artifact_key` | Records image and video metadata for reporting |

### Business Value

Produces campaign-ready ad creatives — copy, images, and video — in a single automated session. The draft-critique-finalize pattern catches weak ideas early, and the image-to-video reference workflow ensures brand-consistent visual storytelling across formats.

---

## 4. AV Studio

**Agent:** `av_editing_studio_agent`
**Models:** Gemini 3 Flash Preview (direction), Gemini 3 Pro Image Preview (reference images), Veo 3.1 Fast (silent video clips), Lyria 2 (music), Chirp 3 HD (voice-over)

### What It Does

Produces broadcast-quality commercials (10s, 15s, or 30s) by compositing AI-generated video clips with professional soundtrack, voice-over, dialogue, and sound effects — delivering a finished commercial that would traditionally require a production crew, recording studio, and editing suite.

### How It Works

- **Step 1 — Storyboard planning:** Creates a trend-driven narrative arc with detailed character sheets (100+ word fixed descriptions), product sheets, camera directions, and scene transitions
- **Step 2 — Reference image generation:** Generates multi-angle character and product reference images to establish visual consistency
- **Step 2.5 — Transition frames (parallel mode):** Pre-generates reference images at each scene cut point, enabling all clips to be produced simultaneously
- **Step 3 — Clip generation:** Produces 8-second silent Veo clips using first/last frame conditioning for visual continuity across scenes; parallel mode generates all clips concurrently (~2 min instead of ~8 min)
- **Step 4 — Audio style selection:** AI-powered recommendation engine suggests optimal voice and music combinations based on brand, audience, and trend context
- **Step 5 — Voice and dialogue:** Generates narration, character dialogue, and branded tagline delivery via Chirp 3 HD with SSML control over pacing, pitch, and emphasis
- **Step 6 — Music and SFX:** Produces custom soundtrack via Lyria 2 and generates scene-specific sound effects
- **Step 7 — Assembly:** Concatenates clips, trims to target duration, and performs professional audio mixing with automatic music ducking during voice-over

### Key Tools

| Tool | Purpose |
|------|---------|
| `generate_subject_image` | Creates character and product reference images |
| `generate_transition_frames` | Pre-generates boundary frames for parallel clip production |
| `generate_clip_with_frames` | Produces an 8-second Veo clip with first/last frame conditioning |
| `generate_clips_parallel` | Generates all clips concurrently using pre-generated frames |
| `concatenate_clips` | Joins clips into a continuous video via ffmpeg |
| `trim_video` | Trims to exact target duration (10s, 15s, or 30s) |
| `generate_commercial_soundtrack` | Creates background music via Lyria 2 |
| `generate_sound_effects` | Produces scene-specific sound effects |
| `generate_voice_over` | Professional narration via Chirp 3 HD with SSML |
| `generate_dialogue` | Multi-character dialogue with distinct voices and emotions |
| `generate_branded_tagline` | Impactful brand tagline with emphasis control |
| `mix_voice_with_audio` | Professional mixing with ducking, EQ, and stereo output |
| `validate_character_consistency` | Gemini vision comparison scoring character fidelity (1-10) |
| `save_commercial_artifact` | Saves final commercial with metadata to session state |

### Business Value

Compresses what traditionally takes weeks of production into minutes. A single agent produces a complete commercial with consistent characters, professional audio, and trend-aligned storytelling — without a camera, studio, or editing bay. Parallel clip generation cuts video production time by 4x.

---

## 5. Focus Group Evaluation

**Agent:** `focus_group_evaluator_agent`
**Model:** Gemini 3 Flash Preview (critic role)

### What It Does

Evaluates a completed commercial through two lenses: objective AI video analysis of the actual footage, and a simulated five-person focus group matched to the target audience demographic. Delivers a scored evaluation with a clear Go/No-Go recommendation.

### How It Works

- **Video analysis:** Sends the commercial MP4 to Gemini for frame-by-frame visual analysis covering scene composition, character consistency, transition quality, production value, and product placement
- **Context review:** Reads campaign metadata, selected ad copies, visual concepts, and trend context from session state
- **Focus group simulation:** Creates 5 distinct panelists matching the target audience profile, each scoring the commercial across 6 weighted categories:
  - Visual Quality (20%)
  - Narrative Consistency (20%)
  - Trend Relevance (15%)
  - Product Integration (15%)
  - Emotional Impact (15%)
  - Audience Appeal (15%)
- **Summary report:** Calculates weighted scores, identifies top 3 strengths and improvement areas, rates uplift potential (Low/Medium/High/Very High), and delivers a Go/No-Go recommendation (threshold: 7.0+)

### Key Tools

| Tool | Purpose |
|------|---------|
| `analyze_commercial_video` | Gemini video understanding for objective visual analysis |

### Business Value

Provides instant, structured creative feedback that traditionally requires recruiting participants, conducting sessions, and compiling reports — a process that takes weeks and thousands of dollars. The weighted scoring system and Go/No-Go threshold give marketing leaders a clear, actionable decision point before media spend.

---

## Architecture

The system is built as a hierarchy of specialized agents orchestrated by a root agent. Each capability operates as an independent skill that can be invoked in sequence or on demand.

```
root_agent (orchestrator)
  |-- trends_and_insights_agent      [Trend Discovery]
  |-- research_orchestrator          [Market Research]
  |     |-- combined_research_pipeline
  |     |     |-- parallel research (YT + GS + Campaign)
  |     |     |-- quality evaluation
  |     |     |-- memory recall + enhanced search
  |     |     +-- report composition
  |     +-- report_saver_agent
  |-- ad_content_generator_agent     [Ad Creative]
  |     |-- ad_creative_pipeline (draft -> critique)
  |     |-- visual_generation_pipeline (draft -> critique -> finalize)
  |     +-- visual_generator (image + video production)
  |-- av_editing_studio_agent        [AV Studio]
  +-- focus_group_evaluator_agent    [Focus Group]
```

For detailed architecture diagrams, see `functional_architecture_diagram.png` and `gcp_architecture_diagram.png` in the project root.

---

## Models and Infrastructure

| Component | Model / Service |
|-----------|----------------|
| Agent orchestration & reasoning | Gemini 3 Flash Preview |
| Image generation | Gemini 3 Pro Image Preview (native, `response_modalities=["IMAGE"]`) |
| Video generation | Veo 3.1 Fast (`veo-3.1-fast-generate-001`) |
| Music generation | Lyria 2 (`lyria-002` via Vertex AI predict) |
| Voice-over & dialogue | Chirp 3 HD (Cloud Text-to-Speech v1beta1) |
| Media fidelity scoring | Gecko (Vertex AI rubric-based evaluation) |
| Search trend data | BigQuery public dataset (`google_trends.top_terms`) |
| Video trend data | YouTube Data API v3 |
| Web research grounding | Google Search (ADK built-in) |
| Campaign memory | Vertex AI Agent Engine Memory Bank |
| Object storage | Google Cloud Storage |
| Secrets management | Google Cloud Secret Manager |
| Agent framework | Google ADK v1.4.2+ |
| Deployment | Google Cloud Run / Vertex AI Agent Engine |

---

## Getting Started

### Run Locally

```bash
# Install dependencies
pip install -U poetry
poetry install

# Set environment variables in trends_and_insights_agent/.env
# Required: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, BUCKET, YT_SECRET_MNGR_NAME

# Start all services
./run_local.sh
# Or run individual components:
#   ADK server: uv run adk web trends_and_insights_agent (port 8000)
#   Frontend:   cd frontend && npm run dev (port 5173)
```

### Deploy to Agent Engine

```bash
# Export requirements and deploy
python deploy_to_ae.py
```

### Autopilot Mode

Set `autopilot_mode: true` in session state to run the full pipeline end-to-end without user confirmations — from trend selection through finished commercial and focus group evaluation.
