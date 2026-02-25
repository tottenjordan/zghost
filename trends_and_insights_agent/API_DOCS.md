# Marketing Intelligence API Documentation

FastAPI backend for the marketing intelligence frontend. Extends ADK's agent execution with parallel dispatch, orchestration tracking, and rating management.

## Quick Start

```bash
# Start the API server
./run_api_server.sh

# Or run directly with poetry
poetry run python -m trends_and_insights_agent.api_server
```

The API will be available at:
- **API Base URL**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Architecture

The API server wraps ADK's `InMemoryRunner` and `InMemorySessionService` with:

1. **Extended Session Management**: Create sessions with preset configs, update state, list artifacts
2. **Parallel Dispatch**: Clone agents and run multiple trend configurations simultaneously
3. **Enhanced Streaming**: SSE streams with multiplexing for parallel executions
4. **Orchestration Tracking**: Monitor active pipelines, execution traces, agent hierarchy
5. **Rating System**: Create rubrics and submit ratings for generated artifacts

## API Endpoints

### Session Management

#### Create Session
```http
POST /api/v1/sessions
Content-Type: application/json

{
  "preset_config": "example_state_pixel",  // optional
  "initial_state": {                        // optional
    "brand": "Google",
    "target_product": "Pixel 9"
  }
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "user_id": "default-user",
  "created_at": "2026-02-24T12:00:00"
}
```

#### Get Session State
```http
GET /api/v1/sessions/{session_id}/state?user_id=default-user
```

**Response:**
```json
{
  "session_id": "uuid",
  "state": {
    "brand": "Google",
    "target_product": "Pixel 9",
    "target_audience": "",
    "target_yt_trends": [],
    "target_search_trends": [],
    ...
  }
}
```

#### Update Session State
```http
PATCH /api/v1/sessions/{session_id}/state?user_id=default-user
Content-Type: application/json

{
  "updates": {
    "brand": "Google",
    "target_product": "Pixel 9 Pro",
    "target_audience": "Tech enthusiasts aged 25-45"
  }
}
```

#### List Session Artifacts
```http
GET /api/v1/sessions/{session_id}/artifacts?user_id=default-user
```

**Response:**
```json
{
  "session_id": "uuid",
  "artifacts": [
    {
      "key": "image_concept_001",
      "version": 1,
      "mime_type": "image/png",
      "size_bytes": 1024000,
      "created_at": "2026-02-24T12:00:00"
    }
  ]
}
```

---

### Agent Execution

#### Run Agent
```http
POST /api/v1/run
Content-Type: application/json

{
  "session_id": "uuid",  // optional, created if not provided
  "user_id": "default-user",  // optional
  "message": "Select a Google trend and YouTube trend"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "user_id": "default-user",
  "stream_url": "/api/v1/run/{session_id}/stream?user_id=default-user&message=..."
}
```

#### Stream Agent Events (SSE)
```http
GET /api/v1/run/{session_id}/stream?user_id=default-user&message=hello
```

**SSE Event Stream:**
```
data: {"type": "AgentStart", "agent_name": "root_agent", "timestamp": "..."}

data: {"type": "ModelResponse", "data": {"text": "..."}, "timestamp": "..."}

data: {"type": "ToolCall", "tool_name": "analyze_youtube_videos", "timestamp": "..."}

data: {"type": "stream_complete", "session_id": "uuid", "timestamp": "..."}
```

---

### Parallel Dispatch

#### Create Parallel Dispatch
```http
POST /api/v1/dispatch
Content-Type: application/json

{
  "streams": [
    {
      "name": "pixel_tech_enthusiasts",
      "session_preset": "example_state_pixel",
      "trend_config": {
        "target_yt_trends": ["AI photography"],
        "target_search_trends": ["smartphone AI"]
      },
      "initial_message": "Generate ad concepts"
    },
    {
      "name": "pixel_photographers",
      "session_preset": "example_state_pixel",
      "trend_config": {
        "target_yt_trends": ["Professional photography"],
        "target_search_trends": ["camera technology"]
      },
      "initial_message": "Generate ad concepts"
    }
  ],
  "max_parallel": 2
}
```

**Response:**
```json
{
  "dispatch_id": "uuid",
  "streams": [
    {
      "stream_id": "uuid",
      "stream_name": "pixel_tech_enthusiasts",
      "session_id": "uuid",
      "status": "pending",
      "created_at": "2026-02-24T12:00:00"
    },
    {
      "stream_id": "uuid",
      "stream_name": "pixel_photographers",
      "session_id": "uuid",
      "status": "pending",
      "created_at": "2026-02-24T12:00:00"
    }
  ],
  "stream_url": "/api/v1/dispatch/{dispatch_id}/stream"
}
```

#### Stream Multiplexed Dispatch (SSE)
```http
GET /api/v1/dispatch/{dispatch_id}/stream
```

**SSE Event Stream:**
```
data: {"stream_id": "uuid", "stream_name": "pixel_tech_enthusiasts", "event": {...}}

data: {"stream_id": "uuid", "stream_name": "pixel_photographers", "event": {...}}

data: {"type": "dispatch_complete", "dispatch_id": "uuid", "streams": [...]}
```

#### Cancel Stream
```http
DELETE /api/v1/dispatch/{dispatch_id}/{stream_id}
```

---

### Orchestration

#### Get Orchestration Status
```http
GET /api/v1/orchestration/status
```

**Response:**
```json
{
  "active_pipelines": [
    {
      "session_id": "uuid",
      "pipeline_name": "research_pipeline",
      "status": "running",
      "agents": [
        {
          "agent_name": "yt_web_planner",
          "status": "running",
          "current_tool": "query_web",
          "started_at": "..."
        }
      ],
      "started_at": "..."
    }
  ],
  "total_sessions": 3
}
```

#### Get Execution Trace
```http
GET /api/v1/orchestration/{session_id}/trace
```

**Response:**
```json
{
  "session_id": "uuid",
  "events": [
    {
      "event_id": "uuid",
      "timestamp": "2026-02-24T12:00:00",
      "agent_name": "root_agent",
      "event_type": "agent_invoked",
      "details": {...},
      "parent_event_id": null
    }
  ],
  "total_events": 42
}
```

#### Get Agent Hierarchy
```http
GET /api/v1/orchestration/agents
```

**Response:**
```json
{
  "root_agent": "root_agent",
  "agents": {
    "root_agent": {
      "name": "root_agent",
      "description": "A trend and insight assistant...",
      "agent_type": "root",
      "sub_agents": ["trends_and_insights_agent", "research_orchestrator", ...],
      "tools": ["save_creatives_and_research_report"],
      "model": "gemini-3-flash-preview"
    },
    "research_orchestrator": {
      "name": "research_orchestrator",
      "description": "Coordinates research pipeline",
      "agent_type": "worker",
      "sub_agents": [],
      "tools": ["combined_research_pipeline"],
      "model": "gemini-3-flash-preview"
    }
  }
}
```

---

### Trends

#### Auto-Select Trends
```http
POST /api/v1/trends/auto-select
Content-Type: application/json

{
  "campaign_config": {
    "brand": "Google",
    "target_product": "Pixel 9",
    "target_audience": ["Tech enthusiasts", "Photographers"],
    "campaign_objectives": ["Increase awareness", "Drive pre-orders"]
  },
  "num_youtube_trends": 3,
  "num_search_trends": 3
}
```

**Note:** Currently returns a placeholder. Full implementation requires integration with trend selection logic.

#### Get Available Trends
```http
GET /api/v1/trends/available
```

**Note:** Currently returns a placeholder. Full implementation requires YouTube and Google Trends API integration.

---

### Ratings

#### Create Rubric
```http
POST /api/v1/rubrics
Content-Type: application/json

{
  "rubric_id": "uuid",  // optional
  "name": "Ad Copy Quality",
  "description": "Evaluates ad copy effectiveness",
  "artifact_type": "ad_copy",
  "criteria": [
    {
      "criterion_id": "relevance",
      "name": "Relevance to Campaign",
      "description": "How well does the ad align with campaign objectives?",
      "scale_min": 1,
      "scale_max": 5,
      "weight": 2.0
    },
    {
      "criterion_id": "clarity",
      "name": "Message Clarity",
      "description": "Is the message clear and easy to understand?",
      "scale_min": 1,
      "scale_max": 5,
      "weight": 1.5
    }
  ]
}
```

#### List Rubrics
```http
GET /api/v1/rubrics
```

#### Get Rubric
```http
GET /api/v1/rubrics/{rubric_id}
```

#### Submit Rating
```http
POST /api/v1/ratings
Content-Type: application/json

{
  "session_id": "uuid",
  "artifact_key": "ad_copy_001",
  "rubric_id": "uuid",
  "ratings": [
    {
      "criterion_id": "relevance",
      "rating": 5,
      "comment": "Perfectly aligned with campaign goals"
    },
    {
      "criterion_id": "clarity",
      "rating": 4,
      "comment": "Clear but could be more concise"
    }
  ],
  "overall_comment": "Excellent ad copy with minor improvements needed",
  "rater_id": "user@example.com"
}
```

**Response:**
```json
{
  "rating_id": "uuid",
  "session_id": "uuid",
  "artifact_key": "ad_copy_001",
  "rubric_id": "uuid",
  "ratings": [...],
  "overall_score": 0.86,  // weighted normalized score 0-1
  "overall_comment": "...",
  "rater_id": "user@example.com",
  "created_at": "2026-02-24T12:00:00"
}
```

#### Get Ratings
```http
GET /api/v1/ratings?session_id=uuid&artifact_key=ad_copy_001&rubric_id=uuid
```

All query parameters are optional. Returns all matching ratings.

---

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-24T12:00:00",
  "active_sessions": 5,
  "active_dispatches": 2,
  "total_ratings": 42,
  "total_rubrics": 3
}
```

---

## Usage Examples

### Example 1: Single Session Workflow

```javascript
// 1. Create session with preset
const sessionResp = await fetch('http://localhost:8000/api/v1/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    preset_config: 'example_state_pixel'
  })
});
const { session_id } = await sessionResp.json();

// 2. Run agent with a message
const runResp = await fetch('http://localhost:8000/api/v1/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id,
    message: 'Select a Google trend and YouTube trend'
  })
});
const { stream_url } = await runResp.json();

// 3. Connect to SSE stream
const eventSource = new EventSource(`http://localhost:8000${stream_url}`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Agent event:', data);
};
```

### Example 2: Parallel Dispatch for A/B Testing

```javascript
// 1. Create parallel dispatch with different trend configs
const dispatchResp = await fetch('http://localhost:8000/api/v1/dispatch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    streams: [
      {
        name: 'variant_a_tech',
        session_preset: 'example_state_pixel',
        trend_config: {
          target_yt_trends: [{ trend_title: 'AI photography' }],
          target_search_trends: [{ trend_title: 'smartphone AI' }]
        },
        initial_message: 'Generate 3 ad concepts'
      },
      {
        name: 'variant_b_lifestyle',
        session_preset: 'example_state_pixel',
        trend_config: {
          target_yt_trends: [{ trend_title: 'Travel photography' }],
          target_search_trends: [{ trend_title: 'vacation photos' }]
        },
        initial_message: 'Generate 3 ad concepts'
      }
    ]
  })
});
const { dispatch_id, stream_url } = await dispatchResp.json();

// 2. Connect to multiplexed stream
const eventSource = new EventSource(`http://localhost:8000${stream_url}`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Event from ${data.stream_name}:`, data.event);
};
```

### Example 3: Rating Generated Artifacts

```javascript
// 1. Create a rubric
const rubricResp = await fetch('http://localhost:8000/api/v1/rubrics', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Ad Copy Quality',
    description: 'Evaluates ad copy effectiveness',
    artifact_type: 'ad_copy',
    criteria: [
      {
        criterion_id: 'relevance',
        name: 'Relevance to Campaign',
        description: 'How well does the ad align with campaign objectives?',
        scale_min: 1,
        scale_max: 5,
        weight: 2.0
      }
    ]
  })
});
const { rubric_id } = await rubricResp.json();

// 2. Submit a rating
const ratingResp = await fetch('http://localhost:8000/api/v1/ratings', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'uuid',
    artifact_key: 'ad_copy_001',
    rubric_id,
    ratings: [
      {
        criterion_id: 'relevance',
        rating: 5,
        comment: 'Perfectly aligned'
      }
    ],
    overall_comment: 'Excellent work'
  })
});

// 3. Get all ratings for a session
const ratingsResp = await fetch(`http://localhost:8000/api/v1/ratings?session_id=uuid`);
const { ratings, average_score } = await ratingsResp.json();
```

---

## Data Models

All request and response models are defined in `trends_and_insights_agent/api_models.py` using Pydantic.

Key models:
- **Session**: `SessionCreateRequest`, `SessionStateResponse`, `SessionArtifactsResponse`
- **Agent Execution**: `AgentRunRequest`, `AgentRunResponse`
- **Parallel Dispatch**: `DispatchConfig`, `StreamConfig`, `DispatchResponse`, `StreamInfo`
- **Orchestration**: `AgentMetadata`, `PipelineStatus`, `TraceEvent`, `ExecutionTraceResponse`
- **Ratings**: `RubricCreateRequest`, `RubricResponse`, `RatingSubmitRequest`, `RatingResponse`

---

## Implementation Notes

### Agent Cloning for Parallel Dispatch

The parallel dispatch feature uses ADK's `agent.clone()` method to create deep copies of the root agent:

```python
cloned_agent = root_agent.clone(update={"name": f"stream_{stream_config.name}"})
```

Each cloned agent:
- Has its own session and state
- Runs independently with its own runner
- Can be configured with different trends
- Streams events to the multiplexed SSE endpoint

### Rate Limiting

The API respects ADK's `rate_limit_callback` which throttles LLM API calls based on:
- `config.rate_limit_seconds` (default: 60)
- `config.rpm_quota` (default: 1000 requests per minute)

When running parallel streams, ensure total request rate stays within quota.

### Session State Persistence

Sessions are stored in-memory via `InMemorySessionService`. For production:
- Consider using ADK's Firestore session service
- Implement session cleanup/expiration
- Add authentication and user management

### CORS Configuration

The API allows CORS requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:3000` (CRA default)
- `http://127.0.0.1:5173`
- `http://127.0.0.1:3000`

Modify `app.add_middleware(CORSMiddleware, ...)` for production origins.

---

## Error Handling

All endpoints return standard HTTP error responses:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

Common status codes:
- `400` - Bad Request (invalid input)
- `404` - Not Found (session, rubric, stream not found)
- `500` - Internal Server Error (unexpected errors)

Errors are logged with full stack traces for debugging.

---

## Development

### Running Tests

```bash
# Run API server tests
poetry run pytest tests/test_api_server.py -v
```

### Adding New Endpoints

1. Define request/response models in `api_models.py`
2. Implement endpoint handler in `api_server.py`
3. Add CORS headers if needed
4. Document in this file
5. Add tests

### Environment Variables

The API inherits environment variables from the agent system:
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `BUCKET` - GCS bucket for artifacts
- `SESSION_STATE_JSON_PATH` - Default preset config

---

## Future Enhancements

- [ ] Implement trend auto-selection with LLM
- [ ] Add WebSocket support for lower-latency streaming
- [ ] Implement session persistence with Firestore
- [ ] Add authentication and user management
- [ ] Add GraphQL endpoint for flexible queries
- [ ] Implement artifact download endpoints
- [ ] Add metrics and monitoring (Prometheus/OpenTelemetry)
- [ ] Rate limiting per user/session
- [ ] Batch operations for ratings
- [ ] Export ratings to CSV/JSON
