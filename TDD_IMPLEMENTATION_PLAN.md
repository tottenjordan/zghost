# zghost TDD Implementation Plan

## Current Status (as of 2026-03-01)

### Verified E2E
- **API 15s commercial**: PASSED (12.6 min, 2 images, 2 videos)
- **Frontend 20s commercial**: PASSED (24.9 min, 4 images, 4 videos)
- Both tests in `tests/api_15s_commercial.py` and `frontend/e2e/vibe-20s.spec.ts`

### CUJ Audit Summary

| CUJ | Feature | Status | Gap |
|-----|---------|--------|-----|
| 1/5 | Campaign Initialization | DONE | PDF upload exists but content not extracted |
| 2/11 | Trend Safety + Grounding | DONE | None |
| 3/10 | Orchestration + Parallel Execution | DONE | None |
| 4 | Voice Control | PARTIAL | No voice → partial re-run |
| 6 | AV Studio (Chirp/Lyria) | PARTIAL | Audio tools fail in E2E (silent commercials) |
| 7 | Evaluation Service | DONE | None |
| 8 | A2A + GE + Historic Runs | PARTIAL | No frontend UI for GE query |
| 9 | Export/Integration | MISSING | No zip/bundle, no Ads API |
| 12 | Granular Agent Retry | MISSING | No partial pipeline re-run |

---

## Phase 1: Audio Reliability + PDF Processing (Foundation)

**Goal**: Fix the two most impactful reliability gaps — audio generation and PDF content extraction.

### 1A. Fix Audio Generation (Voice-Over + Soundtrack)

**Problem**: `generate_voice_over` and `generate_commercial_soundtrack` tools consistently fail in E2E, producing silent commercials.

**Files**:
- `trends_and_insights_agent/skills/av_studio/voice_tools.py`
- `trends_and_insights_agent/skills/av_studio/music_tools.py`
- `trends_and_insights_agent/skills/av_studio/tools.py` (assemble_commercial)

**Fix**:
1. Add retry logic (3 attempts) with exponential backoff to voice and music tool calls
2. Add graceful degradation: if voice-over fails, use text overlay on video instead
3. If soundtrack fails, use a bundled default ambient track (`assets/default_ambient.mp3`)
4. Add diagnostic logging: log exact API error, model version, input params
5. Verify `enable_time_pointing` placement and `AudioConfig` compatibility

**Verification**:
- Run AV studio pipeline → commercial has audio (voice-over OR text overlay)
- Check `session_media/` for generated audio files
- E2E test: commercial artifact has audio track (ffprobe check)

### 1B. PDF Campaign Guide Content Extraction

**Problem**: Backend accepts PDF upload but never extracts text content. Agents can't use the campaign guide.

**Files**:
- `trends_and_insights_agent/shared_libraries/callbacks.py` (line 367: TODO comment)
- `trends_and_insights_agent/api_server.py` (PDF upload endpoint)

**Fix**:
1. After PDF artifact is saved, extract text using `PyPDF2` or `pdfplumber`
2. Store extracted text in session state as `campaign_guide_content`
3. Truncate to 50K chars to fit context windows
4. Root agent instruction: reference `campaign_guide_content` when available
5. Research and ad creative agents use guide content for brand-aligned outputs

**Verification**:
- Upload Pixel marketing guide PDF → `campaign_guide_content` populated in session state
- Research report references guide content
- Ad copies align with guide messaging

### Phase 1 E2E Tests

```bash
# Backend: API test with PDF upload
python tests/api_15s_commercial.py --with-pdf marketing_guide_Pixel_9.pdf

# Frontend: Playwright test with audio verification
cd frontend && npx playwright test e2e/vibe-20s.spec.ts
```

---

## Phase 2: Export Package (CUJ 9)

**Goal**: Users can download a complete campaign package as a zip file.

### 2A. Backend: Campaign Export Endpoint

**Files**:
- `trends_and_insights_agent/api_server.py` (new endpoint)
- `trends_and_insights_agent/api_models.py` (new models)

**Implementation**:
1. New endpoint: `GET /api/v1/sessions/{session_id}/export`
2. Gathers all artifacts from session state:
   - Research report (markdown + PDF)
   - Ad copies (JSON + formatted text)
   - Images (download from GCS)
   - Videos/clips (download from GCS)
   - Commercial (download from GCS)
   - Soundtrack + voice-over (download from GCS)
   - Focus group evaluation (JSON)
   - Campaign config metadata (JSON)
3. Bundles into a zip file with organized directory structure:
   ```
   campaign_export/
   ├── config.json
   ├── research_report.pdf
   ├── ad_copies/
   │   ├── ad_copy_1.txt
   │   └── ad_copy_2.txt
   ├── images/
   │   ├── concept_1.png
   │   └── concept_2.png
   ├── videos/
   │   ├── clip_1.mp4
   │   └── clip_2.mp4
   ├── commercial/
   │   └── commercial_20s.mp4
   ├── audio/
   │   ├── voiceover.mp3
   │   └── soundtrack.mp3
   └── evaluation/
       └── focus_group.json
   ```
4. Returns zip file as streaming download

### 2B. Frontend: Export Button

**Files**:
- `frontend/src/features/orchestration/RunListPage.tsx` (add export button per run)
- `frontend/src/features/studio/StudioPage.tsx` (add export button)
- `frontend/src/services/api.ts` (add export API call)

**Implementation**:
1. "Export Campaign" button on completed runs in RunListPage
2. "Download Package" button in StudioPage header
3. Progress indicator during download
4. File save dialog with suggested filename: `{brand}_{product}_{date}_campaign.zip`

### Phase 2 E2E Tests

```bash
# Backend: Export after pipeline completes
curl -o campaign.zip http://localhost:8000/api/v1/sessions/{session_id}/export
unzip -l campaign.zip  # Verify directory structure

# Frontend: Playwright test
# Click Export button → verify download triggers
```

---

## Phase 3: Granular Agent Retry (CUJ 12)

**Goal**: Users can reject a specific agent output and re-run only that agent without restarting the full pipeline.

### 3A. Backend: Partial Re-run Endpoint

**Files**:
- `trends_and_insights_agent/api_server.py` (new endpoint)
- `trends_and_insights_agent/api_models.py` (new models)

**Implementation**:
1. New endpoint: `POST /api/v1/sessions/{session_id}/rerun`
   ```json
   {
     "agent_name": "ad_copy_drafter",
     "feedback": "Make the copy more energetic and youth-focused",
     "preserve_state_keys": ["combined_final_cited_report", "img_artifact_keys"]
   }
   ```
2. Clears only the target agent's output state keys (e.g., `ad_copy_draft`, `final_select_ad_copies`)
3. Preserves all upstream state (research report, trends, config)
4. Sends a targeted message to the pipeline:
   ```
   "Re-run the ad copy drafting step. Previous output was rejected.
    Feedback: {feedback}. All research and visual assets are preserved."
   ```
5. Returns SSE stream of the partial re-run

### 3B. Agent Retry Mapping

Define which state keys each agent owns (what gets cleared on retry):

| Agent | Output State Keys |
|-------|------------------|
| `research_orchestrator` | `combined_final_cited_report`, `research_sources` |
| `ad_copy_drafter` | `ad_copy_draft`, `final_select_ad_copies` |
| `visual_concept_drafter` | `visual_concepts`, `final_visual_concepts` |
| `visual_generator` | `img_artifact_keys` |
| `av_editing_studio_agent` | `vid_artifact_keys`, `commercial_artifact` |
| `focus_group_evaluator` | `focus_group_evaluation` |

### 3C. Frontend: Retry UI

**Files**:
- `frontend/src/features/orchestration/EvaluationPanel.tsx` (add "Retry" button per agent)
- `frontend/src/features/orchestration/PipelineGraph.tsx` (add retry action on nodes)

**Implementation**:
1. Right-click or button on pipeline graph nodes → "Retry this step"
2. Feedback dialog: "What should change?" → text input
3. Retry triggers partial re-run via new endpoint
4. Pipeline graph updates to show re-running agent
5. Only enabled for completed/error agents (not upstream/running)

### 3D. Voice Command Integration (CUJ 4 Gap)

**Files**:
- `voice_server.py` (add `retry_agent` function tool)

**Implementation**:
1. New voice tool: `retry_agent(agent_name, feedback)`
2. Voice command: "Regenerate the ad copy — make it more energetic"
3. Maps to `POST /api/v1/sessions/{session_id}/rerun`

### Phase 3 E2E Tests

```bash
# Backend: Retry ad copy drafter
curl -X POST http://localhost:8000/api/v1/sessions/{id}/rerun \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"ad_copy_drafter","feedback":"More energetic"}'

# Frontend: Playwright test
# Complete pipeline → click retry on ad_copy_drafter → verify new ad copies
```

---

## Phase 4: Gemini Enterprise Frontend (CUJ 8 Gap)

**Goal**: Users can query the deployed Gemini Enterprise agent directly from the frontend.

### 4A. Backend: GE Query Proxy

**Files**:
- `trends_and_insights_agent/api_server.py` (new endpoint)

**Implementation**:
1. New endpoint: `POST /api/v1/gemini-enterprise/query`
   ```json
   {
     "message": "Create a 15s commercial for Nike Air Max",
     "session_id": "optional-existing-session"
   }
   ```
2. Proxies to Discovery Engine `query_agent()` API
3. Returns streamed response from GE agent
4. Handles authentication via service account

### 4B. Frontend: GE Chat Widget

**Files**:
- `frontend/src/features/gemini-enterprise/GEChatPage.tsx` (new page)
- `frontend/src/App.tsx` (add route)

**Implementation**:
1. New `/gemini-enterprise` page with chat interface
2. Shows Gemini Enterprise branding and agent card info
3. Multi-turn conversation with the deployed GE agent
4. "Open in Gemini Enterprise" link to the GE console
5. Session linking: "Import this session" button to bring GE session into local UI

### Phase 4 E2E Tests

```bash
# Backend: Query GE agent
curl -X POST http://localhost:8000/api/v1/gemini-enterprise/query \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, what can you do?"}'

# Frontend: Playwright test
# Navigate to /gemini-enterprise → send message → verify response
```

---

## Phase 5: Comprehensive E2E Validation

**Goal**: Every CUJ has an automated E2E test that covers both frontend and backend.

### 5A. CUJ Test Matrix

| CUJ | Frontend Test | Backend Test |
|-----|--------------|--------------|
| 1 | Configure wizard → session creation | `POST /api/v1/sessions` with all fields |
| 2 | Trends page → safety badges visible | Safety check API with known-risky trend |
| 3 | Pipeline graph → node status updates | SSE stream → event sequence |
| 4 | Voice command → navigation/config | Voice server WebSocket → tool call |
| 6 | Studio page → all tabs render | Audio generation tools → files created |
| 7 | Eval page → run eval → results display | `POST /api/v1/eval/run` → results |
| 8 | Historic runs → drill-down → artifacts | Session list → state retrieval |
| 9 | Export button → zip download | `GET /api/v1/sessions/{id}/export` |
| 12 | Retry button → partial re-run | `POST /api/v1/sessions/{id}/rerun` |

### 5B. Test Files

```
frontend/e2e/
├── full-pipeline.spec.ts       # Existing: 10s commercial
├── vibe-20s.spec.ts            # Existing: 20s commercial
├── cuj-configure.spec.ts       # NEW: CUJ 1 — campaign config + PDF upload
├── cuj-trends-safety.spec.ts   # NEW: CUJ 2 — trend safety badges
├── cuj-orchestration.spec.ts   # NEW: CUJ 3 — pipeline graph + concurrency
├── cuj-studio.spec.ts          # NEW: CUJ 6 — AV studio tabs + audio
├── cuj-evaluation.spec.ts      # NEW: CUJ 7 — eval run + rubrics
├── cuj-export.spec.ts          # NEW: CUJ 9 — export package
├── cuj-retry.spec.ts           # NEW: CUJ 12 — granular retry
└── cuj-historic-runs.spec.ts   # NEW: CUJ 8 — historic run viewing

tests/
├── api_15s_commercial.py       # Existing: API pipeline test
├── api_export_test.py          # NEW: Export endpoint test
├── api_retry_test.py           # NEW: Partial re-run test
├── api_safety_test.py          # NEW: Trend safety API test
└── api_eval_test.py            # NEW: Evaluation API test
```

### 5C. CI/CD Integration

- Add Playwright E2E tests to GitHub Actions workflow
- Run on PR merge to `gemini3` branch
- Parallel execution of independent CUJ tests
- Screenshot artifacts saved on failure

---

## Implementation Order & Dependencies

```
Phase 1 (Audio + PDF)          ← No dependencies, immediate value
    ↓
Phase 2 (Export)               ← Needs working pipeline (Phase 1)
    ↓
Phase 3 (Granular Retry)       ← Needs stable pipeline + export for validation
    ↓
Phase 4 (GE Frontend)          ← Independent, but benefits from Phase 1-3
    ↓
Phase 5 (E2E Validation)       ← Tests all phases
```

## Estimated Effort

| Phase | Effort | Risk | Priority |
|-------|--------|------|----------|
| Phase 1: Audio + PDF | Medium | Medium (API compatibility) | P0 — Silent commercials are a demo-breaker |
| Phase 2: Export | Medium | Low (straightforward) | P1 — High demo value |
| Phase 3: Granular Retry | High | Medium (state management) | P1 — Key differentiator |
| Phase 4: GE Frontend | Medium | Low (proxy pattern) | P2 — Nice to have |
| Phase 5: E2E Tests | Medium | Low | P0 — Required for confidence |

## Success Criteria

All CUJs pass automated E2E tests:
- **Frontend**: `cd frontend && npx playwright test e2e/ --reporter=html`
- **Backend**: `python -m pytest tests/ -v`
- **Full pipeline**: 15s API + 20s frontend commercials with audio
- **Export**: Zip download with all artifacts
- **Retry**: Partial re-run produces new outputs without full restart
