# Cloud Run Deployment & Voice-Controlled Interface Plan

## Table of Contents

1. [Cloud Run Deployment Architecture](#1-cloud-run-deployment-architecture)
2. [Voice-Controlled Interface Design](#2-voice-controlled-interface-design)
3. [Technical Implementation Steps](#3-technical-implementation-steps)
4. [Risk Assessment & Mitigations](#4-risk-assessment--mitigations)
5. [Phase Timeline](#5-phase-timeline)

---

## 1. Cloud Run Deployment Architecture

### 1.1 Current State

The project currently deploys via `adk deploy cloud_run` in `deploy_to_cloud_run.sh`:

```bash
adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --service_name='trends-and-insights-agent' \
  --with_ui \
  trends_and_insights_agent/
```

**What `adk deploy cloud_run` does under the hood:**

1. Auto-generates a `Dockerfile` (if one does not exist) that installs Python dependencies from `requirements.txt` and runs the ADK API server on port 8000.
2. Builds the container image via Cloud Build.
3. Deploys the image to Cloud Run with the specified service name and region.
4. Configures environment variables (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI`).

**What `--with_ui` provides:**

- Bundles ADK's built-in development web interface (a simple chat UI) into the deployed service.
- Serves the UI at the root URL of the Cloud Run service.
- Useful for testing but **not** the custom React frontend.

### 1.2 Target Architecture: Custom Frontend + API Backend

The production deployment needs two components:

```
                    Internet
                       |
              Cloud Run Service
           (custom Dockerfile)
                       |
            +----------+----------+
            |                     |
      Nginx / Caddy          FastAPI (port 8000)
     (static React build)    trends_and_insights_agent/api_server.py
     /index.html, /assets/*       |
            |                +----+----+
            |                |         |
         React SPA      ADK Runner  Voice WS Proxy
         (Vite build)   /api/v1/*   /ws/* (port 8081)
```

**Option A (Recommended): Single Container, Two Processes**

A single Cloud Run service with a process manager (e.g., `supervisord`) running:
1. The FastAPI API server (`api_server.py`) on port 8000
2. The WebSocket voice server (`voice_server.py`) on port 8081
3. Nginx serving the static React build and reverse-proxying `/api/*` to port 8000 and `/ws/*` to port 8081, listening on Cloud Run's `$PORT` (8080)

**Option B: Two Cloud Run Services**

- **Backend service**: Runs `api_server.py` and `voice_server.py`
- **Frontend service**: Serves the Vite-built static React app via Nginx, proxying API calls to the backend service's internal URL

Option A is simpler for this use case and avoids cross-service authentication complexity.

### 1.3 Networking Requirements

**VPC and Ingress:**
- Default Cloud Run ingress allows all traffic. For production, restrict to `internal-and-cloud-load-balancing` and front with a Cloud Load Balancer with IAP.
- VPC connector is needed if the service must reach private resources (e.g., Cloud SQL, Memorystore). For this project, all external calls go to public Vertex AI/YouTube APIs, so VPC is optional.
- If using a custom domain, configure Cloud Run domain mapping or use a Global HTTP(S) Load Balancer.

**IAM:**
- The Cloud Run service account needs:
  - `roles/aiplatform.user` -- Vertex AI Gemini model calls
  - `roles/storage.objectAdmin` -- GCS bucket read/write for artifacts
  - `roles/secretmanager.secretAccessor` -- YouTube API key from Secret Manager
  - `roles/logging.logWriter` -- Cloud Logging
- For `--no-allow-unauthenticated` (recommended for production): callers need `roles/run.invoker`, or use IAP for browser-based auth.

**WebSocket Support:**
- Cloud Run supports WebSocket connections natively over HTTP/1.1 upgrade.
- Session affinity should be enabled for WebSocket connections (best-effort cookie-based routing).
- WebSocket connections are subject to the same request timeout as HTTP requests.

### 1.4 Custom Dockerfile

Since the default `adk deploy cloud_run` Dockerfile only serves the ADK API, a custom Dockerfile is needed:

```dockerfile
FROM python:3.11-slim

# Install system dependencies (ffmpeg for AV studio)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Copy and build frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Copy and install backend
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY trends_and_insights_agent/ ./trends_and_insights_agent/
COPY voice_server.py .

# Nginx config
COPY deploy/nginx.conf /etc/nginx/nginx.conf

# Supervisord config
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8080
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

### 1.5 Environment Variables & Secrets

**Required environment variables** (set via `gcloud run deploy --set-env-vars` or Cloud Run console):

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI backend | `1` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | `my-project-id` |
| `GOOGLE_CLOUD_PROJECT_NUMBER` | GCP project number | `123456789` |
| `GOOGLE_CLOUD_LOCATION` | Region | `us-central1` |
| `BUCKET` | GCS bucket for artifacts | `my-artifacts-bucket` |
| `YT_SECRET_MNGR_NAME` | Secret Manager key name for YouTube API | `youtube-api-key` |

**Secrets** (mount via Cloud Run secret volumes or environment):

| Secret | Source | Usage |
|--------|--------|-------|
| YouTube API Key | Secret Manager | Trend discovery |
| GitHub Token | Secret Manager | MCP integration (optional) |

### 1.6 Scaling Considerations

**Multi-Agent System Characteristics:**
- Each full pipeline run (trend -> research -> creative -> AV) involves 20+ agent invocations.
- Research phase makes concurrent web requests (3 parallel research streams).
- AV Studio generates 4 sequential Veo clips (30-90s each) plus Imagen images.
- Total end-to-end pipeline runtime: 5-15 minutes.

**Cloud Run Configuration:**

| Setting | Value | Rationale |
|---------|-------|-----------|
| Request timeout | 3600s (60 min) | AV pipeline can take 15+ min with Veo generation |
| Concurrency | 10 | Each request is CPU/memory intensive during agent runs |
| Min instances | 1 | Avoid cold starts for the main pipeline |
| Max instances | 10 | Limit parallel pipeline runs and API costs |
| CPU | 4 | Multi-agent parallel processing needs CPU |
| Memory | 8Gi | ffmpeg video processing, multiple agent contexts in memory |
| CPU always allocated | Yes | Background processing during WebSocket idle periods |

### 1.7 Handling Long-Running Video Generation

Veo clip generation takes 30-90 seconds per clip. The AV studio generates 4 clips sequentially, meaning video generation alone can take 2-6 minutes.

**Strategy: SSE Streaming with Progress Updates**

The current `api_server.py` already implements SSE streaming (`stream_agent_events`). This pattern works well:

1. Client sends a message to `/api/v1/run` and gets back a stream URL.
2. Client opens SSE connection to the stream URL.
3. Backend streams events as agents execute, including:
   - Agent delegation events ("Starting clip 1 generation...")
   - Tool call events (Veo API calls with progress)
   - Completion events with artifact URLs
4. Frontend displays progress in real-time via the orchestration dashboard.

**Timeout Mitigation:**

- Cloud Run max timeout is 60 minutes, which is sufficient for even the longest pipelines.
- SSE connections keep alive with periodic heartbeat events.
- If a connection drops, the client can poll `/api/v1/sessions/{id}/state` to check progress and reconnect.
- The dispatch endpoint (`/api/v1/dispatch`) already supports parallel stream management with status tracking.

**Alternative: Cloud Tasks for Very Long Jobs**

For production reliability, consider offloading AV generation to Cloud Tasks:

1. API receives AV generation request.
2. Creates a Cloud Task that calls a dedicated `/internal/generate-av` endpoint.
3. Frontend polls session state or subscribes to Pub/Sub for completion.
4. Cloud Tasks has a 30-minute timeout and automatic retries.

---

## 2. Voice-Controlled Interface Design

### 2.1 Current Voice Implementation

The existing implementation in `frontend/src/features/voice/` and `voice_server.py` provides:

- **Frontend** (`useVoiceSession.ts`): WebSocket client that records microphone audio at 16kHz PCM, sends base64-encoded audio chunks to the backend, receives and plays 24kHz PCM audio responses.
- **Backend** (`voice_server.py`): WebSocket server on port 8081 that proxies audio between the browser and Gemini Live API via ADK's `Runner.run_live()` with `StreamingMode.BIDI`.
- **UI** (`VoiceBriefAssistant.tsx`): Chat-style interface with audio visualizer, mic toggle, connection state management, and transcript display.
- **Scope**: Currently limited to marketing brief refinement (a standalone voice chat, not integrated with the main pipeline).

### 2.2 Voice Navigation System

**Intent Recognition Architecture:**

The Gemini Live API session receives both audio and text context. By providing a system prompt with navigation intents, Gemini can classify user speech into navigation actions:

```
System Prompt Addition:
"You can help the user navigate the application. When they request navigation,
respond with a special JSON command embedded in your text response:

[NAV:trends] - Navigate to trends page
[NAV:orchestration] - Navigate to orchestration page
[NAV:studio] - Navigate to AV studio
[NAV:rating] - Navigate to rating page
[NAV:voice] - Navigate to voice page
[NAV:narrative] - Navigate to narrative page

Also announce the navigation verbally."
```

**Frontend Command Parser:**

```typescript
// In useVoiceSession.ts, extend the onmessage handler
if (data.mime_type === 'text/plain' && data.role === 'model') {
  const navMatch = data.data.match(/\[NAV:(\w+)\]/);
  if (navMatch) {
    const route = navMatch[1];
    onNavigate?.(`/${route}`);  // callback to React Router
  }
}
```

**Voice Commands -> Routes:**

| Voice Command | Route | Action |
|---------------|-------|--------|
| "Show me the trends" | `/trends` | Navigate to trends page |
| "Go to research" / "Start research" | `/orchestration` | Navigate to orchestration page |
| "Show the commercial" / "Open the studio" | `/studio` | Navigate to AV studio |
| "Rate the results" | `/rating` | Navigate to rating page |
| "Voice mode" | `/voice` | Navigate to voice page |
| "Go back" | Previous route | Navigate back |

### 2.3 Voice-Triggered Pipeline Execution

**Architecture: Voice -> Backend API -> Agent Execution**

The voice server needs to bridge to the main `api_server.py` endpoints. Two approaches:

**Approach A: Tool-Based (Recommended)**

Extend the voice agent with ADK tools that call the API server internally:

```python
# In voice_server.py, add tools to the voice agent
from google.adk.tools import FunctionTool

async def configure_campaign(brand: str, target_audience: str, product: str):
    """Configure campaign metadata via API."""
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"http://localhost:8000/api/v1/sessions/{session_id}/state",
            json={"updates": {
                "brand": brand,
                "target_audience": target_audience,
                "target_product": product,
            }}
        )
    return f"Campaign configured for {brand} targeting {target_audience}"

async def run_research_pipeline(session_id: str):
    """Trigger the research pipeline."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8000/api/v1/run",
            json={"session_id": session_id, "message": "run research pipeline"}
        )
    return "Research pipeline started"

agent = LlmAgent(
    name="voice_marketing_assistant",
    model="gemini-2.0-flash-live-preview-04-09",
    tools=[
        FunctionTool(configure_campaign),
        FunctionTool(run_research_pipeline),
        FunctionTool(select_trends),
        FunctionTool(generate_commercial),
    ],
    ...
)
```

**Voice Commands -> Pipeline Actions:**

| Voice Command | Tool Call | Effect |
|---------------|-----------|--------|
| "Configure campaign for Pixel targeting young professionals" | `configure_campaign(brand="Pixel", target_audience="young professionals", product="Pixel 9")` | Updates session state |
| "Select the top 3 YouTube trends" | `select_trends(source="youtube", count=3)` | Auto-selects trends |
| "Run the research pipeline" | `run_research_pipeline(session_id=...)` | Triggers research orchestrator |
| "Generate a 15-second commercial" | `generate_commercial(duration=15)` | Triggers AV studio |
| "Show me what we have so far" | `get_pipeline_status(session_id=...)` | Reads session state, announces progress |

**Approach B: Structured Output Parsing**

Have Gemini output structured JSON commands that the WebSocket handler parses and dispatches. Less reliable than tool calling but simpler to implement initially.

### 2.4 Voice Feedback for Status Updates

**Real-Time Progress via Voice:**

The voice agent can monitor pipeline status and provide audio updates:

```python
async def announce_progress(session_id: str):
    """Poll session state and announce pipeline progress."""
    state = await get_session_state(session_id)

    stages = [
        ("target_search_trends", "Trend selection complete."),
        ("combined_web_search_insights", "Web research finished."),
        ("final_report_with_citations", "Research report is ready."),
        ("final_select_ad_copies", "Ad copy drafts are done."),
        ("final_select_vis_concepts", "Visual concepts are finalized."),
        ("commercial_artifact", "Your commercial is ready to preview!"),
    ]

    completed = [msg for key, msg in stages if state.get(key)]
    return " ".join(completed) if completed else "Pipeline is still running..."
```

**Status Update Patterns:**

1. **Polling**: Voice agent periodically checks pipeline status and announces changes.
2. **Event-Driven**: Backend pushes status events to the voice WebSocket session when pipeline stages complete.
3. **On-Demand**: User asks "What's the status?" and the agent checks and reports.

**Audio Feedback Design:**

| Event | Voice Announcement | Visual Indicator |
|-------|-------------------|-----------------|
| Pipeline started | "Starting the research pipeline now." | Progress bar appears |
| Research phase complete | "Research is done. I found insights on 3 trends." | Check mark on research step |
| Ad copy drafted | "Ad copy drafts are ready for review." | Copy cards appear |
| Video generation started | "Generating your commercial. This will take a few minutes." | Video progress bar |
| Commercial ready | "Your 30-second commercial is ready! Want me to play it?" | Video player shows |
| Error | "I ran into an issue with [stage]. Want me to retry?" | Error badge |

### 2.5 Technical Architecture

#### WebSocket Proxy on Cloud Run

```
Browser                     Cloud Run Service
  |                              |
  |  WSS /ws/{session_id}        |
  |----------------------------->|  Nginx (port 8080)
  |                              |    |
  |                              |    | proxy_pass ws://127.0.0.1:8081
  |                              |    |
  |                              |  voice_server.py (port 8081)
  |                              |    |
  |                              |    | ADK Runner.run_live()
  |                              |    |
  |                              |  Gemini Live API (WebSocket)
  |<---------audio/text--------->|
```

**Nginx WebSocket Configuration:**

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8081;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

#### Audio Codec Handling

Current implementation uses raw PCM, which works but is bandwidth-intensive:

| Direction | Format | Sample Rate | Bandwidth |
|-----------|--------|-------------|-----------|
| Mic -> Server | 16-bit PCM, mono | 16 kHz | ~256 kbps |
| Server -> Speaker | 16-bit PCM, mono | 24 kHz | ~384 kbps |

**Optimization (Future):**
- Use Opus codec for WebSocket transport (reduces to ~32 kbps).
- Transcode at the proxy layer before sending to Gemini.
- Gemini Live API natively supports PCM, so no server-side transcoding needed for the Gemini leg.

#### Session State Synchronization

The voice session and the UI session must share state:

```
Voice Session (voice_server.py)          API Session (api_server.py)
  |                                           |
  |  Tool call: configure_campaign()          |
  |------------------------------------------>|
  |                                           |  Updates InMemorySession
  |                                           |
  |  Frontend polls GET /sessions/{id}/state  |
  |                                           |<-- React UI
  |                                           |
  |  Tool call: get_pipeline_status()         |
  |<------------------------------------------|
```

**Challenge:** The voice server and API server currently use separate `InMemorySessionService` instances. To share state:

1. **Shared Session Service (Recommended):** Both servers use the same `InMemorySessionService` instance. This requires running them in the same process or using a shared backing store.
2. **HTTP Bridge:** Voice server calls the API server's `/api/v1/sessions/{id}/state` endpoints to read/write state.
3. **External Store:** Use Firestore or Redis as the session backing store, accessible from both servers.

Option 2 (HTTP Bridge) is the simplest to implement immediately. Option 3 (Firestore) is the production-grade solution.

#### Multi-Modal Interaction (Voice + Visual)

The voice assistant should work alongside the visual UI, not replace it:

```
+-------------------------------------------------------+
|  Marketing Intelligence Platform                       |
|                                                        |
|  +------------------------------------------+         |
|  |  [Current Page Content]                   |         |
|  |                                           |         |
|  |  Trends / Research / Studio / etc.        |         |
|  |                                           |         |
|  +------------------------------------------+         |
|                                                        |
|  +------------------------------------------+         |
|  |  Voice Assistant (Floating/Docked)        |         |
|  |  [==== Audio Visualizer ====]             |         |
|  |  User: "Show me the trends"               |         |
|  |  AI: "Navigating to trends page..."       |         |
|  |  [Mic] [Disconnect]                       |         |
|  +------------------------------------------+         |
+-------------------------------------------------------+
```

The `VoiceBriefAssistant` component already supports `isFloating` mode with a fixed-position card. This can be extended to persist across page navigations.

### 2.6 Gemini Live API Capabilities Summary

Based on the current `voice_server.py` and Gemini Live API documentation:

| Capability | Status | Notes |
|------------|--------|-------|
| Bidirectional audio streaming | Implemented | via `StreamingMode.BIDI` |
| Voice Activity Detection | Built-in | Gemini handles turn-taking |
| Audio interruption | Supported | `event.interrupted` is already handled |
| Tool use (function calling) | Supported | ADK `FunctionTool` works in live sessions |
| Text + Audio modalities | Supported | Can switch between `AUDIO` and `TEXT` response |
| Audio transcription | Implemented | Both input and output transcription configured |
| Session memory | Per-session | Context maintained within a live session |
| Voice selection | Implemented | Uses `PrebuiltVoiceConfig` with named voices |

---

## 3. Technical Implementation Steps

### Phase 1: Cloud Run Deployment with Custom Frontend

1. **Create deployment config files:**
   - `deploy/Dockerfile` -- Multi-stage build (Node for frontend, Python for backend)
   - `deploy/nginx.conf` -- Reverse proxy config for API + WS + static files
   - `deploy/supervisord.conf` -- Process manager for nginx + api_server + voice_server

2. **Update `api_server.py`:**
   - Add CORS support for the deployed domain (not just localhost)
   - Add health check endpoint (already exists at `/health`)
   - Configure InMemorySessionService with appropriate TTL

3. **Update `voice_server.py`:**
   - Remove hardcoded `.env` path (use environment variables only)
   - Make port configurable via `$VOICE_WS_PORT` env var (already done)

4. **Create deployment script:**
   - `deploy/deploy_custom.sh` that builds and deploys via `gcloud run deploy`
   - Set all environment variables and secrets
   - Configure timeout, concurrency, and scaling

5. **Test deployment:**
   - Verify frontend loads at service URL
   - Verify API endpoints work through nginx proxy
   - Verify WebSocket voice connection works through nginx proxy
   - Verify SSE streaming works for pipeline execution

### Phase 2: Voice Navigation & Pipeline Integration

1. **Extend voice agent with navigation tools:**
   - Add `navigate_to(page)` tool
   - Add WebSocket message type for navigation commands
   - Update frontend to handle navigation messages

2. **Add pipeline execution tools:**
   - `configure_campaign()` -- Update session state
   - `select_trends()` -- Auto-select trends
   - `run_pipeline()` -- Trigger research/creative/AV pipeline
   - `get_status()` -- Check pipeline progress

3. **State synchronization:**
   - Voice server calls API server endpoints for state management
   - Frontend polls for state changes triggered by voice

4. **Update `VoiceBriefAssistant` component:**
   - Make it persistent across page navigations (lift to `AppShell`)
   - Add navigation callbacks to `useVoiceSession`
   - Display action confirmations in the transcript

### Phase 3: Voice Feedback & Polish

1. **Progress announcements:**
   - Subscribe to pipeline events from the API
   - Convert stage completions to voice announcements
   - Add "What's the status?" query support

2. **Error handling:**
   - Voice announcements for errors
   - Retry suggestions via voice

3. **Multi-modal integration:**
   - Visual highlights when voice mentions a UI element
   - "Read me the ad copy" -- TTS for generated content
   - "Show me clip 3" -- Navigate to specific artifacts

### Phase 4: Production Hardening

1. **Session persistence:**
   - Replace InMemorySessionService with Firestore-backed sessions
   - Shared session store between API and voice servers

2. **Authentication:**
   - Add IAP or Firebase Auth for user authentication
   - Session-based voice identity

3. **Monitoring:**
   - Cloud Logging structured logs
   - Custom metrics for voice session duration, pipeline completion
   - Alerts for error rates and timeout breaches

---

## 4. Risk Assessment & Mitigations

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cloud Run request timeout during AV generation | Pipeline fails mid-generation, wasted Veo API calls | Set 60-min timeout; implement checkpoint/resume for clip generation; save each clip to GCS as it completes |
| WebSocket disconnections on Cloud Run | Voice session drops, user must reconnect | Enable session affinity; implement auto-reconnect in frontend with exponential backoff; persist voice session state |
| Gemini Live API rate limits | Voice sessions throttled or rejected | Implement connection pooling; queue voice sessions if at capacity; show clear user feedback |
| Cold start latency | First request after scale-to-zero takes 15-30s to load all agents | Set min-instances=1; use startup CPU boost; lazy-load agent hierarchy |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| InMemorySessionService data loss on instance restart | All session state lost | Migrate to Firestore sessions for production; implement session export/import |
| Voice command misinterpretation | Wrong pipeline action triggered | Require confirmation for destructive actions ("I'll start the research pipeline. Should I proceed?"); log all voice commands |
| Audio quality issues | Poor transcription, user frustration | Require headphones notice; echo cancellation already enabled; test with various microphones |
| Concurrent pipeline runs overload | Vertex AI quota exceeded, high costs | Limit max concurrent sessions; implement queue with priority; monitor API usage |
| ffmpeg not available in container | AV studio fails | Include ffmpeg in Dockerfile (already planned); test video assembly in CI |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Frontend build fails in Docker | Deployment blocked | Multi-stage build with cached layers; test build in CI before deploy |
| Nginx config errors | Service returns 502 | Validate config with `nginx -t`; use health check endpoint |
| Voice model deprecation | Voice feature breaks | Pin model versions; monitor deprecation notices; have fallback models |

---

## 5. Phase Timeline

### Phase 1: Cloud Run Custom Deployment
**Scope:** Deploy custom frontend + API + voice as a single Cloud Run service.

**Tasks:**
- Create Dockerfile, nginx.conf, supervisord.conf
- Build and deploy to Cloud Run
- Verify all endpoints and WebSocket connectivity
- Configure timeout, scaling, and environment

### Phase 2: Voice Navigation & Pipeline Tools
**Scope:** Add voice commands for navigation and pipeline execution.

**Tasks:**
- Add navigation tools to voice agent
- Add pipeline execution tools (configure, select trends, run, status)
- Implement WebSocket command protocol between voice and frontend
- Integrate floating voice assistant into AppShell

### Phase 3: Voice Feedback & Multi-Modal
**Scope:** Real-time voice progress updates and visual synchronization.

**Tasks:**
- Implement progress polling in voice agent
- Add voice announcements for pipeline stages
- Visual highlights synchronized with voice
- Error reporting via voice

### Phase 4: Production Hardening
**Scope:** Session persistence, auth, monitoring.

**Tasks:**
- Migrate to Firestore-backed sessions
- Add authentication (IAP or Firebase)
- Set up monitoring, logging, and alerting
- Load testing and performance optimization

---

## Appendix A: Nginx Configuration Reference

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    upstream api_server {
        server 127.0.0.1:8000;
    }

    upstream voice_server {
        server 127.0.0.1:8081;
    }

    server {
        listen 8080;
        server_name _;

        # Static frontend files
        root /app/frontend/dist;
        index index.html;

        # API endpoints
        location /api/ {
            proxy_pass http://api_server;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 3600s;
        }

        # ADK endpoints (used by ADK dev UI if enabled)
        location /run {
            proxy_pass http://api_server;
            proxy_set_header Host $host;
            proxy_read_timeout 3600s;
        }

        location /run_sse {
            proxy_pass http://api_server;
            proxy_set_header Host $host;
            proxy_read_timeout 3600s;
            proxy_buffering off;
        }

        location /apps {
            proxy_pass http://api_server;
        }

        location /list-apps {
            proxy_pass http://api_server;
        }

        # Health check
        location /health {
            proxy_pass http://api_server;
        }

        # WebSocket voice proxy
        location /ws/ {
            proxy_pass http://voice_server;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
        }

        # SPA fallback -- serve index.html for all unmatched routes
        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
```

## Appendix B: Supervisord Configuration Reference

```ini
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:api_server]
command=python -m trends_and_insights_agent.api_server
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:voice_server]
command=python voice_server.py
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

## Appendix C: Voice Command Reference

| Category | Command | Action |
|----------|---------|--------|
| Navigation | "Show me the trends" | Navigate to /trends |
| Navigation | "Go to orchestration" / "Start research" | Navigate to /orchestration |
| Navigation | "Open the studio" | Navigate to /studio |
| Navigation | "Rate the results" | Navigate to /rating |
| Navigation | "Go back" | Navigate to previous page |
| Config | "Configure campaign for [brand] targeting [audience]" | Update session state |
| Config | "Set the product to [product]" | Update target_product |
| Config | "Key selling points are [points]" | Update key_selling_points |
| Trends | "Select the top [N] YouTube trends" | Auto-select trends |
| Trends | "Select Google trend about [topic]" | Select specific trend |
| Pipeline | "Run the research pipeline" | Trigger research orchestrator |
| Pipeline | "Generate ad copy" | Trigger ad creative skill |
| Pipeline | "Make a [duration]-second commercial" | Trigger AV studio |
| Status | "What's the status?" | Report pipeline progress |
| Status | "Is the research done?" | Check specific stage |
| Review | "Read me the ad copy" | TTS for generated ad copy |
| Review | "Show me the images" | Navigate to gallery |
| Review | "Play the commercial" | Navigate to studio + play |
