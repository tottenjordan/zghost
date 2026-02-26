# Overnight Deployment Progress Report

**Date**: 2026-02-26
**Branch**: gemini3
**Status**: COMPLETED
**Last Updated**: 2026-02-26 15:45 UTC

---

## Phase 1: Memory Bank Integration (COMPLETED)

### Changes Made
1. **Fixed Vite proxy ordering** - `/api/memories` now routes to memory API (port 8082), not ADK server
2. **Rewrote `memory_api.py`** - Uses `vertexai.Client().agent_engines.memories` SDK (replaced deprecated `aiplatform_v1beta1.MemoryBankServiceClient`)
3. **Created new Agent Engine** - ID: `8576660188117860352` (us-central1) for Memory Bank
4. **Populated campaign memories** - 10 facts consolidated into 6 memories by Memory Bank
5. **Enhanced MemoryExplorer UI** - Create/populate/purge controls, live connection indicator, relevance scores
6. **Updated run_local.sh** - All services use `uv run` for correct ADK 1.25.1 deps

### API Endpoints Working
- `GET /api/memories` - List/search memories (similarity search with `similarity_search_params`)
- `POST /api/memories` - Create single memory
- `POST /api/memories/populate` - Batch generate memories (max 5 per API call)
- `DELETE /api/memories` - Purge all user memories
- `GET /api/memories/health` - Live connectivity probe

### Verification
- All 7 memory integration tests passing (`uv run pytest tests/test_memory_integration.py`)
- Memory Bank API: health, list, search, create, populate verified end-to-end
- Voice server: model `gemini-2.0-flash-live-preview-04-09` verified available, server starts cleanly

### Commit
- `fa64347` - feat: integrate Memory Bank with Vertex AI SDK and fix voice/memory connectivity

---

## Phase 2: Push & Deploy (COMPLETED)

### Step 2.1: Push to remote (COMPLETED)
- Pushed gemini3 branch to origin
- Commit `7de598b` - fix: deploy config for memory API and A2A service

### Step 2.2: Deploy A2A endpoint to Cloud Run (COMPLETED)
- Service: `trends-and-insights-a2a`
- URL: `https://trends-and-insights-a2a-in2bk2mdwa-uc.a.run.app`
- Agent card: `/.well-known/agent.json` serves 57 skills
- Fix: Added `a2a-sdk` dependency (required by `google.adk.a2a.utils.agent_to_a2a`)
- Fix: Cloud Build YAML config to avoid Dockerfile race condition with other deploy scripts

### Step 2.3: Deploy Frontend to Cloud Run (COMPLETED)
- Service: `trends-and-insights-frontend`
- URL: `https://trends-and-insights-frontend-in2bk2mdwa-uc.a.run.app`
- 5 services managed by supervisord: nginx, api_server, adk_server, voice_server, memory_api
- Fix: Changed supervisord to use `uvicorn` directly instead of `python -m` (avoids reload=True double-import issue)
- Fix: Set `min-instances=1` to keep warm instance (cold start takes ~10 min due to root_agent import)
- Fix: Redirected `uv export` stderr to prevent status line polluting requirements.txt

### Step 2.4: Register with Gemini Enterprise (COMPLETED)
- Created Discovery Engine: `grocery-workshop-engine` with `APP_TYPE_INTRANET`
- Created data store: `grocery-workshop-datastore`
- Registered Marketing Intelligence Agent (ID: `7324026170917033413`, state: ENABLED)
- Pattern: `adkAgentDefinition` with `provisionedReasoningEngine` pointing to Agent Engine resource

### Step 2.5: E2E Testing (COMPLETED - ALL PASS)

| Test | Target | Result |
|------|--------|--------|
| Frontend HTML | nginx:8080 | PASS (HTTP 200) |
| API health | api_server:8000 | PASS (healthy) |
| ADK list-apps | adk_server:8001 | PASS (6 apps listed) |
| Memory API health | memory_api:8082 | PASS (connected: true) |
| API v1 agent hierarchy | api_server:8000 | PASS (6 agents, root: root_agent) |
| A2A agent card | A2A service | PASS (57 skills) |
| API create session | api_server:8000 | PASS (session created) |

---

## Phase 3: Architecture Documentation (COMPLETED)

### Deployment Architecture Updates
- Updated DEPLOYMENT_RUNBOOK.md with Memory Bank setup section
- Added A2A Deployment section to DEPLOYMENT_RUNBOOK.md
- Generated deployment architecture diagram (deployment_architecture_with_memory.png)
- Updated docs/diagrams/README.md

---

## Key Configuration

| Item | Value |
|------|-------|
| Project | wortz-project-352116 |
| Project Number | 679926387543 |
| Region | us-central1 |
| Memory Bank Engine ID | 8576660188117860352 |
| GCS Bucket | gs://zghost-media-center |
| Gemini Enterprise Engine | grocery-workshop-engine |
| A2A Service URL | https://trends-and-insights-a2a-in2bk2mdwa-uc.a.run.app |
| Frontend Service URL | https://trends-and-insights-frontend-in2bk2mdwa-uc.a.run.app |
| Registered Agent ID | 7324026170917033413 |

---

## Issues Encountered & Fixes

### Session 1 (Overnight)
1. **Agent Engine not found** - Old ID `6534772537337839616` was deleted. Created new engine `8576660188117860352`.
2. **Vite proxy ordering** - `/api` matched before `/api/memories`, routing memory requests to wrong server.
3. **Memory API wrong SDK** - Was using `aiplatform_v1beta1` instead of `vertexai.Client()`.
4. **retrieve() response wrapper** - `RetrieveMemoriesResponseRetrievedMemory` wraps memory in `.memory` property.
5. **Max 5 direct memories per generate() call** - Had to implement batching.

### Session 2 (Morning)
6. **A2A missing dependency** - `a2a-sdk` package not in requirements; needed by `google.adk.a2a.utils.agent_to_a2a`. Fixed with `uv add a2a-sdk`.
7. **A2A Dockerfile race condition** - `deploy_custom.sh` and `deploy_a2a.sh` both copied Dockerfiles to root. Fixed with Cloud Build YAML config referencing `deploy/Dockerfile.a2a` directly.
8. **Discovery Engine creation** - Requires at least one data store. Created `grocery-workshop-datastore` first.
9. **Discovery Engine app type** - Must use `APP_TYPE_INTRANET` with `SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT` for agent support.
10. **api_server 502 on Cloud Run** - `python -m` invocation triggered `uvicorn.run(reload=True)` causing a double-import failure. Fixed by using `uvicorn` directly in supervisord.conf.
11. **9.5-minute cold start** - `root_agent` import loads all agents, skills, tools, and model configs. Set `min-instances=1` to keep a warm instance.
12. **uv export status line** - `uv export` printed `Resolved N packages in Xms` to stdout, polluting requirements.txt. Fixed with `2>/dev/null` redirect.

---

## Files Changed (Session 2)

| File | Change |
|------|--------|
| `deploy/supervisord.conf` | Use uvicorn directly for api_server; add startsecs=10 |
| `deploy/deploy_custom.sh` | Set min-instances=1; fix uv export stderr |
| `deploy/deploy_a2a.sh` | Fix uv export stderr |
| `pyproject.toml` | Add a2a-sdk dependency |
| `uv.lock` | Updated with a2a-sdk |

---

## Summary

All three phases are complete:
- **Phase 1**: Memory Bank integration working locally and deployed
- **Phase 2**: Both Cloud Run services deployed, Gemini Enterprise agent registered, 7/7 E2E tests passing
- **Phase 3**: Architecture documentation and diagrams updated

### Known Limitations
- **Cold start**: ~10 minutes due to heavy root_agent import. Mitigated with `min-instances=1`
- **Agent Engine registration**: Used `provisionedReasoningEngine` pattern (requires an existing Agent Engine resource); alternative A2A/Cloud Run registration patterns were not supported by the Discovery Engine API at time of implementation
