# Trends & Insights

> A multi-agent marketing intelligence system that transforms real-time cultural trends into broadcast-ready advertising campaigns — from research to finished commercial — in under 15 minutes.

<p align="center">
  <img src='docs/pipeline_stages.png' width="800"/>
</p>

## What It Does

Trends & Insights is an AI-powered marketing platform that:

1. **Discovers trends** — surfaces what consumers care about right now from Google Search and YouTube
2. **Conducts research** — runs parallel market research across three dimensions (search trends, YouTube trends, campaign brief) and synthesizes a cited report
3. **Creates ad campaigns** — writes ad copy, generates campaign images, and produces 15-second commercials with AI video (Veo 3.1)
4. **Evaluates quality** — runs a simulated focus group with AI-generated panelist portraits and weighted scoring
5. **Delivers a PDF report** — compiles research, creatives, commercial, and focus group evaluation into a single downloadable artifact

The entire pipeline runs autonomously on [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/docs/reasoning-engine/overview), orchestrated by a deterministic state machine (no LLM decision-making at the top level).

## Architecture

<p align="center">
  <img src='docs/functional_architecture_diagram.png' width="800"/>
</p>

### GCP Architecture

<p align="center">
  <img src='docs/gcp_architecture_diagram.png' width="800"/>
</p>

> Architecture diagrams are being actively updated — see `docs/` for the latest versions.

### Pipeline Stages

![Campaign Pipeline Stages](docs/pipeline_stages.png)

### Models & Services

| Component | Model / Service |
|-----------|----------------|
| Agent reasoning | Gemini 3 Flash Preview |
| Image generation | Imagen 4 (generate_images API) |
| Video generation | Veo 3.1 Fast |
| Voice-over & dialogue | Chirp 3 HD |
| Music generation | Lyria 2 |
| Media fidelity scoring | Gecko (Vertex AI rubric-based evaluation) |
| Search trends | BigQuery (`google_trends.top_terms`) |
| Video trends | YouTube Data API v3 |
| Web research | Google Search grounding |
| Campaign memory | Vertex AI Memory Bank |
| Agent runtime | Vertex AI Agent Engine |

## Quick Start

### Prerequisites

- Google Cloud project with billing enabled
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- YouTube Data API key stored in Secret Manager

### 1. Clone and install

```bash
git clone https://github.com/tottenjordan/zghost.git
cd zghost
pip install uv
uv sync
```

### 2. Enable Google Cloud APIs

```bash
gcloud auth application-default login

gcloud services enable \
    aiplatform.googleapis.com \
    bigquery.googleapis.com \
    storage-component.googleapis.com \
    secretmanager.googleapis.com \
    youtube.googleapis.com \
    texttospeech.googleapis.com \
    run.googleapis.com \
    discoveryengine.googleapis.com
```

### 3. Create YouTube API key

Follow [these instructions](https://developers.google.com/youtube/v3/getting-started) to get a YouTube Data API key, then store it in Secret Manager:

```bash
echo -n "YOUR_API_KEY" | gcloud secrets create yt-data-api --data-file=-
```

### 4. Create GCS bucket

```bash
gcloud storage buckets create gs://YOUR_BUCKET_NAME --location=us-central1
```

### 5. Configure environment

Create `trends_and_insights_agent/.env`:

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_PROJECT_NUMBER=123456789
GOOGLE_CLOUD_LOCATION=global
BUCKET=gs://your-bucket-name
YT_SECRET_MNGR_NAME=yt-data-api
```

### 6. Run locally

```bash
# Start all services (ADK server + frontend + voice + memory API)
./run_local.sh

# Or just the ADK server:
uv run adk web trends_and_insights_agent
```

Open [http://localhost:8000](http://localhost:8000) and select the agent from the dropdown.

## Deploy to Agent Engine

Agent Engine is the recommended deployment target for production use. It provides managed sessions, memory, and observability.

### Deploy

```bash
source trends_and_insights_agent/.env
uv run python deploy_to_ae.py --step agent-engine --update
```

This deploys the `CampaignOrchestrator` as a Vertex AI Reasoning Engine. The engine ID is saved to `deployment_info.json`.

### Run E2E on Agent Engine

The E2E runner creates a session with pre-populated campaign data and runs the full pipeline:

```bash
source trends_and_insights_agent/.env
uv run python e2e_demo_runner.py
```

**Quality gates** (all must pass):
- Research report > 500 chars with citations
- 1+ campaign images generated
- 15s commercial video via Veo 3.1
- Focus group evaluation with Go/No-Go score
- Final PDF report saved as artifact

### Publish to Gemini Enterprise

After deploying to Agent Engine, register with Gemini Enterprise (Discovery Engine):

```bash
# Register agent with GE (reads engine ID from deployment_info.json)
source trends_and_insights_agent/.env
uv run python deploy_to_ae.py --step gemini-enterprise
```

Or deploy everything in one command:

```bash
# Deploy to Agent Engine + register with GE
source trends_and_insights_agent/.env
uv run python deploy_to_ae.py --step all --update
```

The GE agent ID is saved to `deployment_info.json` for use by tests and the streamAssist API.

## Agent Engine Observability

The system provides full observability when running on Agent Engine.

### Dashboard
<img src='docs/agent_engine_screenshots/ae_dashboard_overview.png' width="800"/>

Sessions, agent latency (P50/P95/P99), invocation counts, and error rates.

### Tools
<img src='docs/agent_engine_screenshots/ae_tools_dashboard.png' width="800"/>

Per-tool call counts, P95 duration, and error rates across 30+ tool calls per campaign run.

### Cloud Trace
<img src='docs/agent_engine_screenshots/ae_cloud_trace_session_spans.png' width="800"/>

End-to-end distributed tracing with span-level detail for each pipeline stage.

## Project Structure

![Project Structure](docs/project_structure.png)

## Autopilot Mode

Set `autopilot_mode: true` in session state to run the full pipeline end-to-end without user confirmations — from trend selection through finished commercial and focus group evaluation. The E2E runner uses this mode by default.

## Gemini Enterprise Integration

The agent is accessible through Gemini Enterprise (Discovery Engine) via the `streamAssist` API. GE provides an enterprise chat interface with thinking visualization, status chips, and artifact display.

### How It Works

1. **Agent Engine deployment** creates a Vertex AI Reasoning Engine (`8788263399906607104`)
2. **GE registration** creates an agent entry in the Discovery Engine that routes to the reasoning engine
3. **streamAssist API** sends user queries through GE, which delegates to the ADK agent via `agentsSpec`

### Key IDs (from `deployment_info.json`)

| ID | Purpose |
|----|---------|
| `engine_id` | Agent Engine (Reasoning Engine) ID |
| `ge_engine` | Discovery Engine app ID |
| `ge_agent_id` | GE agent ID (routes to reasoning engine) |

### streamAssist API

```bash
TOKEN=$(gcloud auth print-access-token)

curl -s -X POST \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/global/collections/default_collection/engines/GE_ENGINE/assistants/default_assistant:streamAssist" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"text": "Create a campaign for Tide Fabric Softener"},
    "agentsSpec": {"agentSpecs": [{"agentId": "GE_AGENT_ID"}]},
    "session": "projects/PROJECT_NUMBER/locations/global/collections/default_collection/engines/GE_ENGINE/sessions/-"
  }'
```

**`agentsSpec` is required** — without it, GE answers with generic Gemini knowledge instead of routing to the ADK agent. Use `sessions/-` to auto-create a new session.

### Manage GE Agents

```bash
# List registered agents
uv run python -m deploy.register_gemini_enterprise list --from-deployment-info

# Register (idempotent — skips if exists)
uv run python -m deploy.register_gemini_enterprise register --from-deployment-info

# Delete
uv run python -m deploy.register_gemini_enterprise delete --agent-id AGENT_ID --from-deployment-info
```

## Gemini Enterprise Demo Script

Use this script when recording or presenting a live demo in the Gemini Enterprise browser UI.

### Setup

1. Open Gemini Enterprise: `https://vertexaisearch.cloud.google.com`
2. Navigate to the engine (link in `deployment_info.json` or your GE console)
3. Ensure the agent is registered: `uv run python deploy_to_ae.py --step all --update`

### Demo Flow

**Step 1 — Kickoff (paste into GE chat)**

```
@trends2insights Create a full marketing campaign for Tide Fabric Softener with Hibiscus Scent.

Brand: Tide
Product: Tide Fabric Softener with Hibiscus Scent
Target Audience: Gen Z eco-conscious consumers
Key Selling Points: New Hibiscus Scent, Plant-based formula, 2x cleaning power, Biodegradable packaging

Run in autopilot mode - auto-select trend 1 for both search and YouTube trends, then proceed through research, ad creative, image generation, 15s video commercial, focus group evaluation, and final PDF campaign brief.
```

> The `@trends2insights` prefix is required to route the message to the ADK agent instead of generic Gemini.

**Step 2 — Watch the pipeline**

The agent will show its thinking process and progress through:
- Trend analysis and research synthesis
- Ad creative generation (headlines, body copy, CTAs)
- Campaign image generation (hero product shots + lifestyle images)
- Video commercial (15s via Veo 3.1)
- Focus group evaluation
- Final PDF campaign brief

**Step 3 — Follow-up prompts** (if pipeline pauses)

```
@trends2insights continue
```

```
@trends2insights Can you generate a 15-second video commercial based on the ad creative?
```

```
@trends2insights Create a final PDF campaign brief with the generated assets
```

### What to Highlight

| Moment | Talking Point |
|--------|--------------|
| Research synthesis | "The agent runs 3 parallel research streams — YouTube trends, Google Search, and campaign analysis — then merges and evaluates the findings" |
| Ad creative | "Ad copy is drafted, critiqued by a separate critic agent, then the top 3 ideas are selected for image generation" |
| Image generation | "Each idea gets 2 shots — a hero product shot and a lifestyle scene — all scored by Gecko for brand fidelity" |
| Video commercial | "Veo 3.1 generates a cinematic 15-second commercial using campaign images as style/asset references" |
| Focus group | "A simulated 3-person panel evaluates the campaign with weighted scoring and a Go/No-Go threshold" |
| PDF report | "Everything compiles into a branded PDF with campaign context, research, creative assets, and focus group results" |

### Automated E2E Test (for validation before demo)

```bash
# Run the full pipeline via AE API + capture GE browser screenshots
source trends_and_insights_agent/.env
DISPLAY=:20 uv run python tests/ge_browser_demo_critic.py
```

This drives the pipeline via the Agent Engine API, then opens the GE browser to capture screenshots and runs a Gemini vision critic to evaluate the demo quality.

## Video Walkthrough

> Overview of the end-to-end workflow

[![demo](https://img.youtube.com/vi/S8Bh4eBQSs0/hqdefault.jpg)](https://www.youtube.com/watch?v=S8Bh4eBQSs0)

## FAQ

**Q: How long does a full pipeline run take?**

~10–15 minutes on Agent Engine. Research takes 3–5 minutes (parallel streams), creative 3–5 minutes (image gen + Veo), and focus group + PDF ~2 minutes.

**Q: Why does the pipeline get stuck on "Thinking" in Gemini Enterprise?**

This usually means a sub-agent is running a long operation (image gen, video gen) without emitting status updates. The fix is `ui:status_update` state_delta events emitted BEFORE each LLM call via `before_model_status_callback`. If you see this, redeploy: `uv run python deploy_to_ae.py --step agent-engine --update`.

**Q: Why do images fail to generate on Agent Engine?**

Imagen 4's `generate_images()` API is synchronous and can timeout on AE's ~60s wave budget. Workaround: pre-generate images locally and pre-populate them in session state. See `tests/ge_browser_demo_critic.py` for the pre-generation pattern.

**Q: How do I test before a live demo?**

```bash
# Automated critic test — runs pipeline + browser screenshots + Gemini vision scoring
source trends_and_insights_agent/.env
DISPLAY=:20 uv run python tests/ge_browser_demo_critic.py
```

Target score: 7.0+ (passing), 9.0+ (CEO-ready).

**Q: What does `autopilot_mode` do?**

Skips all user confirmations. Trends are auto-selected (#1 ranked), research runs without approval gates, and creative proceeds without user review. The E2E runner and demo critic both use autopilot mode.

**Q: How do I add a new brand/product for a demo?**

No code changes needed. Just change the message sent to the agent. The pipeline is brand-agnostic — it adapts research queries, ad copy, and visual concepts to whatever brand/product/audience you specify.

**Q: What's the `@trends2insights` prefix in GE?**

It routes your message to the ADK agent instead of generic Gemini. Without it, GE answers with its own knowledge. The agent must be registered first via `deploy_to_ae.py --step gemini-enterprise`.

**Q: How does Memory Bank work?**

Campaign insights are automatically saved after each pipeline run and retrieved at the start of new sessions. This lets the agent learn from past campaigns (e.g., "last time we targeted Gen Z with hibiscus, the focus group scored 7.8"). Memory Bank uses `VertexAiMemoryBankService` on the same Agent Engine instance.

**Q: What if the pipeline loops infinitely on a stage?**

Each stage has loop guards: `_focus_group_attempts` (cap 5), `_creative_pipeline_attempts` (cap 15), `_av_studio_runs` (cap 5). The SAVE_REPORT stage always sets `final_report_with_citations` even on failure to prevent re-entry. If you hit a loop, check Cloud Logging for the stage name and counter values.

## Detailed Documentation

- [Capability Overview](docs/CAPABILITIES.md) — detailed breakdown of each pipeline stage with tools, models, and business value
- [NovaStorm Design](docs/NOVASTORM.md) — skill self-reflection and evolution system
- [NovaStorm Integration](docs/NOVASTORM_INTEGRATION.md) — how to wire NovaStorm into the pipeline
- [Skill Critic Agent](docs/skill_critic.md) — scores skill outputs using GEPA
- [Research Pipeline Orchestrator](docs/staged_researcher.md) — deterministic research pipeline
- [Trends & Insights Agent](docs/trend_assistant.md) — captures metadata and fetches trends

