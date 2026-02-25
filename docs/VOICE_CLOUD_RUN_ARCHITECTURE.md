# Voice-Controlled Cloud Run Deployment Architecture

## 1. Overview

The marketing intelligence platform includes a voice-controlled interface powered by the Gemini Live API. Users can speak to a marketing brief assistant, navigate the UI with voice commands, and trigger pipeline actions hands-free. The voice system runs as a WebSocket server co-located with the API and ADK servers inside a single Cloud Run container, fronted by nginx.

Voice commands enhance the UI by allowing users to navigate between pages ("go to trends"), configure campaign parameters ("set brand to Pixel"), and control pipeline execution ("start the pipeline") without touching the keyboard. Commands are parsed client-side from transcript text, so navigation happens instantly without a server round-trip.

## 2. Cloud Run Deployment Architecture

### Container Layout

The Cloud Run service runs a single container managed by supervisord, which starts three backend processes plus nginx as the entry point:

```
Cloud Run Service (port 8080)
|
+-- nginx (port 8080, Cloud Run's $PORT)
|     |-- /              --> Static React frontend (/app/frontend/dist)
|     |-- /api/          --> API Server (proxy to 127.0.0.1:8000)
|     |-- /apps, /run*   --> ADK Server (proxy to 127.0.0.1:8001)
|     |-- /ws/           --> Voice WebSocket Server (proxy to 127.0.0.1:8081)
|     +-- /health        --> API Server health check
|
+-- supervisord
      |-- [program:api_server]    python -m trends_and_insights_agent.api_server  (port 8000)
      |-- [program:adk_server]    adk web --port 8001 trends_and_insights_agent   (port 8001)
      +-- [program:voice_server]  python voice_server.py                          (port 8081)
```

See `docs/diagrams/cloud_run_architecture.png` and `docs/diagrams/deployment_architecture.png` for visual diagrams.

### How the Voice Server Integrates

The voice server (`voice_server.py`) is a standalone Python WebSocket server using the `websockets` library. It runs alongside the API and ADK servers as a separate supervisord program. All three processes share the same container filesystem, environment variables, and GCP service account credentials.

The voice server creates an ADK `Runner` with an `LlmAgent` configured for the `gemini-2.0-flash-live-preview-04-09` model in `StreamingMode.BIDI`. Each WebSocket connection gets its own `LiveRequestQueue` and `InMemorySessionService` session. Audio flows bidirectionally between the browser and Gemini Live API through this proxy.

### Port Mapping

| Service | Internal Port | Exposed Via |
|---------|--------------|-------------|
| API Server (FastAPI) | 8000 | nginx `/api/` proxy |
| ADK Web Server | 8001 | nginx `/apps`, `/run`, `/run_sse` proxy |
| Voice WebSocket Server | 8081 | nginx `/ws/` proxy with WebSocket upgrade |
| nginx (entry point) | 8080 | Cloud Run `$PORT` |

### nginx Routing Rules

nginx handles four traffic types:

1. **Static files** -- The React SPA is served from `/app/frontend/dist`. Unmatched routes fall back to `index.html` for client-side routing.

2. **API requests** (`/api/`) -- Proxied to the FastAPI server on port 8000. SSE support is enabled with `proxy_buffering off` and `proxy_cache off`. Read/send timeouts are set to 3600s for long-running pipeline operations.

3. **ADK endpoints** (`/apps`, `/run`, `/run_sse`, `/list-apps`) -- Proxied to the ADK web server on port 8001. The `/run_sse` endpoint has SSE-specific settings for streaming agent events.

4. **WebSocket connections** (`/ws/`) -- Proxied to the voice server on port 8081. The nginx config includes the required WebSocket upgrade headers:

```nginx
location /ws/ {
    proxy_pass http://voice_server;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_buffering off;
}
```

### Dockerfile Structure

The container uses a multi-stage build (`deploy/Dockerfile`):

- **Stage 1** (`node:20-slim`): Builds the React frontend with Vite, producing static assets in `/app/frontend/dist`.
- **Stage 2** (`python:3.11-slim`): Installs system dependencies (ffmpeg, nginx, supervisor), Python packages, the ADK agent, the voice server, and copies the built frontend from Stage 1.

The final image exposes port 8080 and starts supervisord as the entry command.

## 3. WebSocket Scaling Considerations

### Session Affinity

Cloud Run session affinity should be enabled so that WebSocket connections from the same client are routed to the same container instance. This is configured at deploy time:

```bash
gcloud run deploy ... --session-affinity
```

Session affinity uses a best-effort cookie-based routing mechanism. It is not guaranteed during scale-up events, but for voice sessions it prevents unnecessary reconnections.

### Connection Lifecycle and Timeouts

- Cloud Run supports a maximum request timeout of **60 minutes**, which applies to WebSocket connections.
- The voice server configures `ping_interval=20` and `ping_timeout=20` to keep connections alive and detect stale clients.
- nginx sets `proxy_read_timeout` and `proxy_send_timeout` to 3600s (1 hour), matching the Cloud Run maximum.
- When a WebSocket connection closes (client navigates away, network drop), the voice server's `finally` block calls `live_request_queue.close()` to clean up the Gemini Live API session.

### Horizontal Scaling

Each Cloud Run instance can handle multiple concurrent voice sessions. Key factors:

| Factor | Value | Notes |
|--------|-------|-------|
| Memory per voice session | ~10-20 MB | Audio buffers, ADK runner context, Gemini session state |
| Recommended concurrency | 10-20 voice sessions per instance | With 8Gi memory |
| CPU per active session | Minimal | Audio is proxied, not processed; Gemini handles speech recognition |
| Max WebSocket message size | 10 MB | Set via `max_size=10*1024*1024` in the voice server |

### Memory Considerations

Audio buffers are the primary memory consumer per connection:

- **Input audio chunks**: 4096 samples x 2 bytes = 8 KB per chunk at 16 kHz (~4 chunks/second = ~32 KB/s).
- **Output audio**: Base64-encoded PCM at 24 kHz, buffered transiently during playback.
- **ADK session state**: `InMemorySessionService` stores session context in-process. Each session consumes memory proportional to conversation history length.

For a container with 8Gi memory, the practical limit is approximately 50-100 concurrent voice sessions, well within typical usage patterns.

## 4. Voice Server Integration Patterns

### Cloud Run Mode (Current)

The voice server runs co-located with the API server inside the same Cloud Run container.

```
Browser <-- WSS --> Cloud Run Container
                      |-- nginx (8080)
                      |-- api_server (8000)
                      |-- adk_server (8001)
                      +-- voice_server (8081) --> Gemini Live API
```

**Advantages:**
- Low latency: voice server communicates with the API server over localhost (`127.0.0.1`)
- Simple deployment: single container, single `gcloud run deploy` command
- Shared authentication: all services use the same Cloud Run service account
- Shared environment: all processes read the same environment variables and secrets

**Trade-offs:**
- Memory pressure: audio processing and agent execution compete for the same instance memory
- Coupled scaling: voice and API traffic scale together, even if demand patterns differ
- Single point of failure: if the container restarts, all active voice sessions disconnect

### Agent Engine Mode (Alternative)

For production deployments with higher scale requirements, the voice server can run as a separate Cloud Run service while the agent backend runs on Agent Engine.

```
Browser <-- WSS --> Voice Cloud Run Service
                      +-- voice_server.py --> Agent Engine (remote)
                                                +-- ADK agents
                                                +-- Managed sessions
```

**Advantages:**
- Independent scaling: voice connections and agent compute scale separately
- Agent Engine manages agent lifecycle, session persistence, and model serving
- Voice server becomes a thin WebSocket proxy with lower resource requirements

**Trade-offs:**
- Additional network hop between voice server and Agent Engine backend
- More complex authentication: service-to-service auth between Cloud Run and Agent Engine
- Higher latency for tool calls that need to round-trip to Agent Engine

## 5. Security Considerations

### Audio Data Handling

- Audio is transmitted as raw 16-bit PCM over WebSocket (input at 16 kHz, output at 24 kHz).
- No audio data is persisted to disk or cloud storage. All audio processing happens in-memory.
- Audio buffers are released when the WebSocket connection closes.

### Authentication

- **Service-to-service**: The Cloud Run service account authenticates to Vertex AI (Gemini Live API), GCS, and Secret Manager using IAM roles.
- **User sessions**: Each WebSocket connection generates a unique session ID (`voice-{timestamp}`). In production, this should be tied to authenticated user identity via IAP or Firebase Auth.
- **Cloud Run IAM**: For non-public deployments, callers need `roles/run.invoker`. Browser access can be gated with Identity-Aware Proxy (IAP).

### Session Isolation

- Each WebSocket connection creates a separate `InMemorySessionService` session and `LiveRequestQueue`.
- Sessions are identified by a unique ID extracted from the WebSocket URL path (`/ws/{session_id}`).
- No cross-session data sharing occurs; each voice session has its own agent context and conversation history.

### CORS and Origin Validation

- The voice server sets `origins=None` in the `websockets.serve()` call, which disables origin checking. For production, restrict this to the deployed domain.
- nginx proxies WebSocket connections with the original `Host`, `X-Real-IP`, and `X-Forwarded-For` headers preserved.
- The frontend constructs WebSocket URLs relative to `window.location.host`, ensuring same-origin connections.

### Transcript Privacy

- Input and output audio transcriptions are generated by the Gemini Live API and forwarded to the browser for display.
- Transcripts are held in browser memory (React state) and not sent to any logging backend by default.
- Server-side, the voice server logs session lifecycle events (connect, disconnect) but does not log audio content or transcripts.

## 6. Latency Optimization

### Co-location

Running the voice server in the same container as the API server eliminates network latency for internal calls. When the voice agent needs to read or write session state, it communicates with the API server over `127.0.0.1`.

### Cold Start Mitigation

Voice sessions are latency-sensitive. Use Cloud Run's `min-instances` to keep at least one warm instance:

```bash
gcloud run deploy ... --min-instances=1
```

Cold starts on `python:3.11-slim` with all dependencies take approximately 15-30 seconds. A warm instance responds to WebSocket connections in under 100ms.

### Audio Chunk Size

The frontend uses a `ScriptProcessorNode` with a buffer size of **4096 samples** at 16 kHz. This produces ~256ms audio chunks, balancing:

- **Latency**: Smaller chunks (1024, 2048) reduce latency but increase WebSocket message overhead.
- **Overhead**: Larger chunks (8192) reduce overhead but add perceptible delay.
- **4096 samples**: A practical compromise yielding ~4 messages/second with acceptable latency.

### Gemini Live API Streaming

The ADK `Runner.run_live()` method streams responses incrementally. The voice server forwards each audio part to the browser as it arrives, rather than buffering the complete response. This reduces time-to-first-audio-byte to the Gemini API's own streaming latency (typically under 500ms).

### Client-Side Sample Rate Conversion

The frontend handles sample rate differences entirely client-side:

- **Microphone capture**: `AudioContext` at 16 kHz, converted to 16-bit PCM before sending.
- **Playback**: Received 24 kHz PCM from Gemini is decoded and played via an `AudioContext` buffer created at the correct sample rate (`GEMINI_SAMPLE_RATE = 24000`). This prevents pitch/speed distortion without server-side transcoding.

## 7. Voice Command Architecture

### Client-Side Command Parsing

Voice commands are parsed entirely in the browser. When Gemini transcribes user speech, the transcript text appears in React state. The `useVoiceCommands` hook monitors the transcript and matches user messages against a set of regex patterns defined in `COMMAND_PATTERNS`.

```
User speaks --> Gemini Live API transcribes --> transcript text arrives via WebSocket
                                                      |
                                                useVoiceCommands hook
                                                      |
                                              regex pattern matching
                                                      |
                                              action dispatch (navigate, set config, etc.)
```

This approach avoids a server round-trip for navigation commands. The user says "go to trends," Gemini transcribes it, and the browser navigates immediately.

### Pattern Matching

Commands are matched using regex patterns in `useVoiceCommands.ts`:

| Pattern | Intent | Action |
|---------|--------|--------|
| `go to trends` | `navigate` | `navigate('/trends')` |
| `go to orchestration` | `navigate` | `navigate('/orchestration')` |
| `start the pipeline` | `start_pipeline` | `setPipelineStatus('running')` |
| `set brand to [X]` | `set_brand` | `setCampaignConfig({ brand: X })` |
| `select trend [X]` | `select_trend` | Log for future integration |

Each matched command receives a confidence score of 0.9 (high confidence for exact pattern matches).

### Action Dispatch

The `useVoiceCommands` hook dispatches commands through two mechanisms:

- **React Router** (`useNavigate`): For `navigate` intents, the hook calls `navigate(path)` to change the current route.
- **Zustand store** (`useCampaignStore`): For configuration and pipeline intents, the hook updates global state via `setCampaignConfig` and `setPipelineStatus`.

### Visual Feedback

The `VoiceCommandRouter` component renders a toast notification when a command executes. It displays the command type and a human-readable description (e.g., "Navigating to Trends") for 3 seconds before auto-hiding.

### Future: Server-Side Intent Classification

For complex commands that cannot be reliably captured by regex (e.g., "find me a trending topic about sustainability and start the research"), server-side intent classification using Gemini function calling would provide higher accuracy. The voice agent would be extended with ADK `FunctionTool` definitions for pipeline actions, and Gemini would classify intent and extract parameters from natural speech.

## 8. Monitoring and Observability

### Cloud Run Metrics

Cloud Run provides built-in metrics via Cloud Monitoring:

- **Request count**: Total HTTP and WebSocket connections over time.
- **Request latency**: P50/P95/P99 latency for HTTP requests. WebSocket connections show as long-lived requests.
- **Container instance count**: Active instances and scaling events.
- **Memory utilization**: Critical for tracking audio buffer pressure with concurrent voice sessions.
- **CPU utilization**: Should remain low since audio is proxied, not processed.

### WebSocket Connection Tracking

The voice server logs session lifecycle events:

- `Voice session started: session={id} audio={bool}` -- on WebSocket connect.
- `Downstream ended` / `Upstream ended` -- on connection close.

For production, add structured logging with session duration, message counts, and error codes to enable dashboards and alerting.

### Voice Session Metrics

Key metrics to track:

| Metric | Source | Purpose |
|--------|--------|---------|
| Active voice connections | voice_server connection count | Capacity planning |
| Session duration | Time between connect and disconnect | Usage patterns |
| Commands recognized | `useVoiceCommands` dispatch count | Feature adoption |
| Command success rate | Commands dispatched / user messages | Voice UX quality |
| Audio chunk throughput | WebSocket messages/second | Performance monitoring |

### Error Tracking

Common failure modes to monitor:

- **WebSocket disconnects**: Unexpected `onclose` events without prior `disconnect()` call. May indicate network issues or Cloud Run instance preemption.
- **Gemini Live API errors**: Forwarded to the client as `{"type": "error", "message": "..."}`. Track error rates by error type.
- **Audio processing failures**: `playAudio` exceptions in the browser (logged to console). Could indicate malformed PCM data or AudioContext issues.
- **Supervisord restarts**: If the voice server crashes and supervisord restarts it (`autorestart=true`), all active sessions are lost. Monitor restart counts via Cloud Logging.

## 9. Future Considerations

### AudioWorklet Migration

The current implementation uses `ScriptProcessorNode` for microphone audio capture, which is deprecated in the Web Audio API. Migration to `AudioWorklet` would:

- Move audio processing to a dedicated thread, reducing main-thread jank.
- Provide more precise buffer timing and lower latency.
- Ensure long-term browser compatibility.

### Multi-Language Voice Support

The Gemini Live API supports multiple languages. To enable multi-language voice:

- Add a language selector to the voice UI.
- Pass the selected language in the `RunConfig` speech configuration.
- Update command patterns in `useVoiceCommands.ts` for localized command phrases.

### Voice Authentication

Speaker verification could enable:

- Hands-free login by recognizing enrolled speakers.
- Role-based access control tied to voice identity.
- Audit trails linked to specific speakers rather than session IDs.

### Offline Command Buffering

When the WebSocket connection drops temporarily:

- Buffer voice commands locally in the browser.
- Replay buffered commands when the connection is re-established.
- Use the `connectionState` machine to queue actions during `connecting` and `error` states.

### Opus Codec Compression

The current raw PCM transport uses ~256-384 kbps per direction. Switching to Opus codec would reduce bandwidth to ~32 kbps, improving performance on constrained networks. This would require client-side Opus encoding and server-side transcoding before forwarding to the Gemini Live API.
