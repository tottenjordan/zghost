# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent marketing intelligence system built with Google's Agent Development Kit (ADK). It analyzes trends, conducts research, generates creative content (images, video, commercials), evaluates quality via simulated focus groups, and produces comprehensive PDF campaign reports — all orchestrated by a deterministic BaseAgent state machine.

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: Google ADK v1.25.1+
- **AI Models**: Gemini 3 Flash Preview, Gemini 3 Pro Image Preview, Veo 3.1 Fast, Lyria 2, Chirp 3 HD
- **Package Manager**: uv (via pyproject.toml)
- **Cloud**: Google Cloud Platform (Vertex AI Agent Engine, GCS, Secret Manager, BigQuery)

## Development Commands

### Initial Setup

```bash
pip install uv
uv sync
```

### Running Locally

```bash
# Start all services (ADK + frontend + voice + memory)
./run_local.sh

# Or run individual components:
uv run adk web trends_and_insights_agent     # ADK server (port 8000)
cd frontend && npm run dev                    # Frontend (port 5173)
```

### Deploy to Agent Engine

```bash
source trends_and_insights_agent/.env
uv run python deploy_to_ae.py --step agent-engine --update
```

### E2E Testing

```bash
# Run full pipeline on Agent Engine (Tide Fabric Softener campaign)
source trends_and_insights_agent/.env
uv run python e2e_demo_runner.py
```

## Architecture

### Pipeline (Deterministic State Machine — Flat 2-Level)

```
CampaignOrchestrator (BaseAgent) — orchestrator.py
  TRENDS      → deterministic (BigQuery + YouTube API, no LLM)
  RESEARCH    → research_agent (single LLM, google_search + recall_prior_insights)
  AD_CREATIVE → ad_creative_agent (single LLM, draft/critique/select ad copies + visual concepts)
  IMAGE_GEN   → deterministic SDK (Imagen 4) — 3 ASSET reference images:
                  product ASSET, person ASSET, trend ASSET
                  Each scored with Gecko fidelity
  AV_STUDIO   → deterministic SDK (Veo 3.1) — single clip with ASSET references
  FOCUS_GROUP → focus_group_evaluator_agent (single LLM)
  SAVE_REPORT → save_final_report_tool (direct call, no LLM) — branded PDF
  COMPLETE
```

**Total: 3 LLM agents, 2 nesting levels, 0 output_keys**

### Key Directories

- `trends_and_insights_agent/` - Main agent module
  - `orchestrator.py` - CampaignOrchestrator (top-level BaseAgent state machine, all stages inlined)
  - `agent.py` - Agent wiring (orchestrator + 3 sub-agents)
  - `flat_agents.py` - research_agent and ad_creative_agent definitions
  - `skills/focus_group/` - Focus group evaluator agent
  - `common_agents/` - Legacy sub-agent definitions (tools still used)
  - `shared_libraries/` - Config, utils, callbacks, fidelity eval
- `e2e_demo_runner.py` - Agent Engine E2E test runner
- `deploy_to_ae.py` - Agent Engine deployment script
- `docs/` - Capability docs, architecture diagrams
- `tests/` - Test suite

## Agent Engine Deployment

- **Engine ID**: `8788263399906607104` (us-central1)
- **Memory Bank**: Consolidated into the same engine (no separate engine needed)
- **Project**: `wortz-project-352116` / `679926387543`
- Deploy: `uv run python deploy_to_ae.py --step agent-engine --update`
- Engine info stored in `deployment_info.json`

## Environment Variables

Required in `trends_and_insights_agent/.env`:

- `GOOGLE_GENAI_USE_VERTEXAI=1`
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_PROJECT_NUMBER` - GCP project number
- `GOOGLE_CLOUD_LOCATION=global` - Required for Gemini 3 models
- `BUCKET` - GCS bucket (e.g., `gs://zghost-media-center`)
- `YT_SECRET_MNGR_NAME` - YouTube API key secret name
- `MEMORY_BANK_AGENT_ENGINE_ID=8788263399906607104` - Memory Bank engine (same as agent runtime)

## Important Patterns

1. **Flat 2-Level Architecture**: Single CampaignOrchestrator (BaseAgent) with 3 LLM sub-agents (research, ad_creative, focus_group). No nested orchestrators. All image/video gen is deterministic SDK calls in the orchestrator.
2. **State Persistence on AE**: Use `event.actions.state_delta["key"] = value` — direct `state["key"] = value` does NOT persist across AE invocations. Also write to `ctx.session.state[key]` for same-invocation reads.
3. **`_run_agent_and_capture` Pattern**: Orchestrator runs sub-agent, captures longest non-thought text from events, persists via state_delta. Replaces `output_key` which doesn't survive AE waves.
4. **Per-Event Persistence**: Emit state_delta AFTER each operation (image gen, video gen) — AE waves can timeout mid-operation
5. **Wave-Safe Veo**: Submit Veo operation, poll for 45s, save operation name to state if not done, resume on next wave via `GenerateVideosOperation(name=op_name)` stub
6. **Trend-Driven Creative**: Ad copies must reference specific trend titles by name. Visual concepts and image prompts incorporate brand, trends, and ad headlines from state.
7. **ASSET-Only References**: All 3 reference images (product, person, trend) are ASSET type. Veo only supports one reference type per call.
8. **Gecko Fidelity**: Images auto-scored against product description; regenerated if score < 0.7
9. **Focus Group**: Simulated 3-person panel with portrait generation, weighted scoring, Go/No-Go threshold at 7.0
10. **Memory Bank**: `VertexAiMemoryBankService` for cross-campaign learning; `recall_prior_insights` tool in research
11. **Status Updates**: `ui:status_update` state_delta for GE status chips; `before_model_status_callback` on all LLM agents
