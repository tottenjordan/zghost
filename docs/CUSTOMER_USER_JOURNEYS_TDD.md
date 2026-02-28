# Customer User Journeys — Technical Design Document

## Overview

This document describes the end-to-end customer user journeys (CUJs) through the Trends & Insights multi-agent marketing intelligence platform. The system enables users to go from campaign configuration to a finished commercial with AI-generated research, creative assets, and automated focus-group evaluation.

### System Architecture

```
Browser (React SPA)
  ├── /trends           → Campaign wizard (4-step config)
  ├── /orchestration    → Pipeline execution & approval
  ├── /narrative        → Research report review
  ├── /studio           → AV commercial playback
  └── /rating           → Manual rating (optional)
         │
         ▼
    Vite Dev Proxy / nginx (prod)
         │
    ┌────┴──────────────────────────────────────┐
    │  api_server.py (FastAPI, port 8000)        │
    │  ├── POST /api/v1/sessions                 │
    │  ├── GET  /api/v1/sessions/:id/state       │
    │  ├── PATCH /api/v1/sessions/:id/state      │
    │  ├── GET  /api/v1/run/:id/stream (SSE)     │
    │  └── GET  /api/v1/orchestration/:id/events │
    └────┬──────────────────────────────────────┘
         │
    ┌────┴──────────────────────────────────────┐
    │  ADK Agent Runtime (root_agent)            │
    │  ├── trend_discovery skill                 │
    │  ├── market_research skill                 │
    │  ├── ad_creative skill                     │
    │  ├── av_studio skill                       │
    │  └── focus_group skill                     │
    └────┬──────────────────────────────────────┘
         │
    ┌────┴──────────────────────────────────────┐
    │  External Services                         │
    │  ├── Gemini 3 (Flash / Pro Image)          │
    │  ├── Imagen 4.0 Ultra                      │
    │  ├── Veo 3.1 Fast                          │
    │  ├── Google Cloud Storage                  │
    │  ├── YouTube Data API                      │
    │  ├── Google Trends API                     │
    │  └── Memory Bank (Vertex AI Agent Engine)  │
    └───────────────────────────────────────────┘
```

### Pipeline Flow

```
Campaign Config → Trend Selection → Launch
  → Research (parallel: YouTube + Google Search + Campaign)
  → Research Report → Narrative Review (accept/skip)
  → Ad Creative (copy draft→critique, visual draft→critique→finalize)
  → Image Generation (Imagen) + Video Generation (Veo)
  → AV Studio (commercial assembly: intro/body/outro/soundtrack)
  → Focus Group Evaluation (6-category scoring, Go/No-Go)
```

---

## CUJ-1: Campaign Setup & Trend Selection

### Entry Point

`/trends` — 4-step wizard (Configure → Trends → Evaluation → Review)

### Step 1: Configure

The user enters campaign metadata:

| Field | Input Type | Example |
|-------|-----------|---------|
| Brand | Text input | "Google Pixel" |
| Target Product | Text input | "Pixel 9 smartphone" |
| Target Audience | Text input | Demographics, psychographics, lifestyle |
| Key Selling Points | Textarea | Camera features, AI capabilities |

**Preset support**: Config can be pre-filled via localStorage (`campaign-store` key) using a JSON profile like `example_state_pixel.json`.

**API**: Config is stored client-side in Zustand store (persisted to localStorage).

### Step 2: Trends

Two tabs: **Google Search Trends** and **YouTube Trends**.

- Trends are fetched on page load (or from backend cache)
- User selects 1+ trends from each category via checkboxes
- Selected trends are stored in `selectedSearchTrends` / `selectedYtTrends`

### Step 3: Evaluation

User reviews or customizes the evaluation rubric (default 6-category rubric pre-loaded).

### Step 4: Review

Summary of all selected config, trends, and rubrics. User clicks **"Add Execution Run to Orchestrator"** to launch.

### State Keys Written

| Key | Type | Description |
|-----|------|-------------|
| `brand` | string | Brand name |
| `target_product` | string | Product name |
| `target_audience` | string[] | Audience segments |
| `key_selling_points` | string[] | Product features |
| `target_search_trends` | `{ target_search_trends: SearchTrend[] }` | Selected Google trends |
| `target_yt_trends` | `{ target_yt_trends: YTTrend[] }` | Selected YouTube trends |

### Success Criteria

- All config fields are non-empty
- At least 1 Google trend and 1 YouTube trend selected
- Navigation to `/orchestration` after launch

### Error Cases

- Trend API fetch failure → retry button or manual entry
- Empty config → "Save Configuration" button disabled
- No trends selected → launch button disabled

---

## CUJ-2: Pipeline Execution & Approval Flow

### Entry Point

`/orchestration` — main pipeline execution page

### Pipeline Start

1. User selects **commercial duration** (10s / 15s / 30s) via `select#duration`
2. User clicks **"Start Pipeline"**
3. Frontend creates a session via `POST /api/v1/sessions` with initial state (config + trends + duration)
4. Frontend opens SSE stream via `GET /api/v1/run/{sessionId}/stream?message=start`
5. Chat panel shows real-time agent activity

### Approval Gates

The pipeline pauses at several points to request human approval. The agent poses a question and the UI shows **"Approve All"** and **"Revise"** buttons.

| Gate | Agent | Typical Prompt | User Action |
|------|-------|---------------|-------------|
| 1 | `trends_and_insights_agent` | "I found these trends, shall I proceed?" | Approve / Revise |
| 2 | `research_orchestrator` | "Research plan ready, proceed?" | Approve / Revise |
| 3 | `ad_content_generator_agent` | "Ad concepts ready, proceed with generation?" | Approve / Revise |
| 4 | `visual_generator` | "Visual concepts finalized, generate images/videos?" | Approve / Revise |
| 5 | `av_editing_studio_agent` | "Commercial script ready, produce the video?" | Approve / Revise |
| 6 | `focus_group_evaluator_agent` | "Run focus group evaluation?" | Approve / Revise |

**Approval detection**: The UI checks if the last agent message contains question marks or keywords like "approve", "proceed", "look good", "ready to". When detected, quick-action buttons appear.

**Approval action**: Clicking "Approve All" injects the message `"Looks good, proceed with all options."` as a user message and opens a new SSE stream with that message.

### SSE Event Protocol

Events stream as Server-Sent Events with the following structure:

```
event: agent_step
data: {"agentName":"research_orchestrator","parts":[{"text":"..."}],"timestamp":"..."}

event: tool_call
data: {"agentName":"gs_web_searcher","toolName":"google_search","args":{...}}

event: tool_result
data: {"agentName":"gs_web_searcher","result":"..."}

event: state_update
data: {"key":"combined_final_cited_report","value":"..."}

event: done
data: {"status":"completed"}
```

### State Keys Written (per phase)

| Phase | Key | Type |
|-------|-----|------|
| Research | `combined_final_cited_report` | string (markdown) |
| Research | `draft_pdf_url` | string (GCS URL) |
| Research | `sources` | Record<string, string> |
| Creative | `final_select_ad_copies` | object[] |
| Creative | `img_artifact_keys` | `{ img_artifact_keys: ArtifactKey[] }` |
| Creative | `vid_artifact_keys` | `{ vid_artifact_keys: ArtifactKey[] }` |
| AV Studio | `commercial_artifact` | string or `{ artifact_key: string }` |
| Focus Group | `focus_group_evaluation` | object (scores + recommendation) |

### Success Criteria

- SSE stream connects and delivers events
- All approval gates are passed (auto or manual)
- Pipeline progresses through all 5 skills sequentially

### Error Cases

- SSE connection drop → frontend auto-reconnects on user action
- Agent error → error event in chat, user can retry
- Timeout → pipeline continues in background; user can poll state

---

## CUJ-3: Research Review & Iteration

### Entry Point

`/narrative?session={sessionId}` — accessed via banner in orchestration or direct URL

### Flow

1. Page loads session state via `GET /api/v1/sessions/{id}/state`
2. If `combined_final_cited_report` exists, displays the research report
3. If `draft_pdf_url` or `final_pdf_url` exists, shows embedded PDF iframe
4. User can chat with the agent to iterate on the report
5. Two action buttons:
   - **"Accept Report"** → sends acceptance message, navigates to `/orchestration`
   - **"Skip to Creative"** → navigates directly to `/orchestration`

### State Keys Read

| Key | Type | Description |
|-----|------|-------------|
| `combined_final_cited_report` | string | Full research report (markdown) |
| `draft_pdf_url` | string | GCS URL for PDF version |
| `final_pdf_url` | string | GCS URL for final PDF |
| `sources` | Record<string, string> | Citation map |

### Success Criteria

- Report text or PDF iframe is visible
- Chat input allows iteration
- Accept → navigates back to orchestration
- Skip → navigates back to orchestration

### Error Cases

- No report ready → page shows loading state
- PDF URL expired → fallback to text display
- Chat iteration fails → error message in chat

---

## CUJ-4: Creative Review & Artifact Gallery

### Entry Point

`/orchestration` → **Results** tab

### Artifact Types

| Type | State Key | Display |
|------|-----------|---------|
| Ad Copies | `final_select_ad_copies` | Text cards with headline, body, CTA |
| Images | `img_artifact_keys` | Image gallery with captions |
| Videos | `vid_artifact_keys` | Video gallery with playback |

### Artifact Key Shape

```typescript
interface ArtifactKey {
  artifact_key: string;    // GCS path
  headline?: string;
  concept?: string;
  caption?: string;
  img_prompt?: string;     // For images
  vid_prompt?: string;     // For videos
  trend?: string;          // Associated trend
}
```

GCS paths are converted for display: `gs://bucket/path` → `https://storage.googleapis.com/bucket/path`

### Success Criteria

- At least 2 images displayed
- At least 2 videos displayed
- Ad copy cards show headline + body
- Media loads and plays correctly

### Error Cases

- GCS URL not accessible → broken image/video placeholder
- Artifact keys empty → "No results yet" message

---

## CUJ-5: AV Production & Commercial Playback

### Entry Point

`/studio?session={sessionId}` — accessed via banner or direct URL

### Commercial Structure

The AV Studio agent assembles a commercial from:

| Duration | Clips | Structure |
|----------|-------|-----------|
| 10s | 3-4 | Intro (2s) + Body (6s) + Outro (2s) |
| 15s | 4-6 | Intro (3s) + Body (9s) + Outro (3s) |
| 30s | 8-12 | Intro (5s) + Body (20s) + Outro (5s) |

Components:
- **Intro**: Brand/product hook with trending topic
- **Body**: Feature demos with creative visuals
- **Outro**: Call to action, brand logo
- **Soundtrack**: AI-generated background music

### State Keys

| Key | Type | Description |
|-----|------|-------------|
| `commercial_artifact` | string or object | GCS path to final commercial |
| `commercial_duration` | 10 \| 15 \| 30 | Selected duration |

### Success Criteria

- Video player visible with commercial loaded
- Commercial duration matches selection (within 2s tolerance)
- Video plays when clicked

### Error Cases

- Commercial still generating → loading indicator
- GCS URL not accessible → error message
- Video codec not supported → download link fallback

---

## CUJ-6: Focus Group Evaluation

### Entry Point

`/orchestration` → **Eval** tab (runs automatically after commercial generation)

### Evaluation Rubric

The focus group evaluator scores the commercial across 6 weighted categories:

| Category | Weight | Description |
|----------|--------|-------------|
| Visual Quality | 20% | Production value, image/video quality |
| Narrative Consistency | 20% | Story coherence, message clarity |
| Trend Relevance | 15% | Connection to selected trends |
| Product Integration | 15% | Natural product feature showcase |
| Emotional Impact | 15% | Audience emotional response |
| Audience Appeal | 15% | Demographic targeting effectiveness |

### Scoring

- Each category: 1-10 scale
- Weighted average calculated
- **Go/No-Go recommendation**:
  - Score >= 7.0 → "Go" (ready for campaign)
  - Score 5.0-6.9 → "Conditional Go" (minor revisions)
  - Score < 5.0 → "No-Go" (significant revisions needed)

### State Keys

| Key | Type | Description |
|-----|------|-------------|
| `focus_group_evaluation` | object | Scores, feedback, recommendation |

### Success Criteria

- All 6 categories scored
- Weighted average calculated
- Go/No-Go recommendation provided
- Evaluation visible in Eval tab

### Error Cases

- Commercial not available → evaluation skipped
- Agent timeout → retry or manual evaluation

---

## CUJ-7: Full E2E (All CUJs Combined)

### Timing Expectations

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Campaign Setup | 1-2 min | 1-2 min |
| Research | 5-10 min | 6-12 min |
| Narrative Review | 1-2 min | 7-14 min |
| Ad Creative | 5-10 min | 12-24 min |
| AV Production | 5-10 min | 17-34 min |
| Focus Group | 2-3 min | 19-37 min |

**Total**: ~25-35 min for a 10s commercial

### Checkpoint Map

```
START
  │
  ├── [1] Config saved → brand, target_product, target_audience, key_selling_points
  ├── [2] Trends selected → target_search_trends, target_yt_trends
  ├── [3] Pipeline started → session created, SSE connected
  ├── [4] Research done → combined_final_cited_report (non-empty string)
  ├── [5] Report reviewed → narrative accept/skip
  ├── [6] Images generated → img_artifact_keys.img_artifact_keys.length >= 2
  ├── [7] Videos generated → vid_artifact_keys.vid_artifact_keys.length >= 2
  ├── [8] Commercial done → commercial_artifact matches /commercial_10s/
  ├── [9] Focus group done → focus_group_evaluation present
  │
  END
```

### Final Assertion Checklist

| # | Assertion | State Key | Condition |
|---|-----------|-----------|-----------|
| 1 | Brand set | `brand` | non-empty string |
| 2 | Product set | `target_product` | non-empty string |
| 3 | Audience set | `target_audience` | non-empty string or array |
| 4 | Selling points set | `key_selling_points` | non-empty string or array |
| 5 | Google trends selected | `target_search_trends.target_search_trends` | length > 0 |
| 6 | YouTube trends selected | `target_yt_trends.target_yt_trends` | length > 0 |
| 7 | Research report | `combined_final_cited_report` | non-empty string |
| 8 | Images generated | `img_artifact_keys.img_artifact_keys` | length >= 2 |
| 9 | Videos generated | `vid_artifact_keys.vid_artifact_keys` | length >= 2 |
| 10 | Commercial produced | `commercial_artifact` | contains "commercial" |
| 11 | Focus group scored | `focus_group_evaluation` | present |

---

## Session State Schema Reference

### Campaign Configuration Keys

| Key | Type | Set By | Read By |
|-----|------|--------|---------|
| `brand` | string | UI / preset | All skills |
| `target_product` | string | UI / preset | All skills |
| `target_audience` | string \| string[] | UI / preset | Research, Creative |
| `key_selling_points` | string \| string[] | UI / preset | Research, Creative |
| `commercial_duration` | 10 \| 15 \| 30 | UI | AV Studio |

### Trend Keys

| Key | Type | Set By | Read By |
|-----|------|--------|---------|
| `target_search_trends` | `{ target_search_trends: SearchTrend[] }` | Trend Discovery | Research, Creative |
| `target_yt_trends` | `{ target_yt_trends: YTTrend[] }` | Trend Discovery | Research, Creative |

### Research Keys

| Key | Type | Set By | Read By |
|-----|------|--------|---------|
| `combined_final_cited_report` | string | Research | Narrative, Creative |
| `draft_pdf_url` | string | Research | Narrative |
| `final_pdf_url` | string | Research | Narrative |
| `sources` | Record<string, string> | Research | Narrative |
| `prior_campaign_insights` | string | Memory Bank | Research |

### Creative Keys

| Key | Type | Set By | Read By |
|-----|------|--------|---------|
| `final_select_ad_copies` | object[] | Ad Creative | Results gallery |
| `img_artifact_keys` | `{ img_artifact_keys: ArtifactKey[] }` | Ad Creative | Results, AV Studio |
| `vid_artifact_keys` | `{ vid_artifact_keys: ArtifactKey[] }` | Ad Creative | Results, AV Studio |

### Production Keys

| Key | Type | Set By | Read By |
|-----|------|--------|---------|
| `commercial_artifact` | string \| `{ artifact_key: string }` | AV Studio | Studio page |
| `focus_group_evaluation` | object | Focus Group | Eval tab |
| `gcs_folder` | string | System | All skills (GCS upload path) |

---

## API Reference

### Create Session

```
POST /api/v1/sessions
Body: {
  "preset_config": { ... },     // optional: initial campaign config
  "initial_state": { ... }      // optional: additional state keys
}
Response: {
  "session_id": "string",
  "user_id": "default-user",
  "created_at": "ISO8601"
}
```

### Get Session State

```
GET /api/v1/sessions/:sessionId/state?user_id=default-user
Response: {
  "session_id": "string",
  "state": { ...all state keys... }
}
```

### Update Session State

```
PATCH /api/v1/sessions/:sessionId/state?user_id=default-user
Body: {
  "updates": { "key": "value", ... }
}
Response: { "status": "ok" }
```

### Start Pipeline (SSE Stream)

```
GET /api/v1/run/:sessionId/stream?user_id=default-user&message=<text>
Response: text/event-stream

Events:
  event: agent_step
  data: { "agentName": "...", "parts": [{"text": "..."}], "timestamp": "..." }

  event: tool_call
  data: { "agentName": "...", "toolName": "...", "args": {...} }

  event: tool_result
  data: { "agentName": "...", "result": "..." }

  event: state_update
  data: { "key": "...", "value": ... }

  event: done
  data: { "status": "completed" }
```

### Get Orchestration Events

```
GET /api/v1/orchestration/:sessionId/events
Response: {
  "session_id": "string",
  "events": [ ...AgentEvent[]... ],
  "total_events": number
}
```

### Memory Bank API (port 8082)

```
POST /api/memories/create
Body: { "facts": ["string", ...], "scope": { "user_id": "..." } }

POST /api/memories/retrieve
Body: { "query": "string", "scope": { "user_id": "..." } }
```
