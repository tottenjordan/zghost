# Backend API Implementation Summary

This document summarizes the FastAPI backend implementation for the marketing intelligence frontend.

## Files Created

### Core Implementation
1. **`trends_and_insights_agent/api_server.py`** (941 lines)
   - FastAPI application with lifecycle management
   - Session management (create, get state, update state, list artifacts)
   - Agent execution with SSE streaming
   - Parallel dispatch with agent cloning
   - Orchestration tracking and monitoring
   - Rating system with rubrics
   - Health check endpoint

2. **`trends_and_insights_agent/api_models.py`** (333 lines)
   - Pydantic models for all request/response schemas
   - Session models: `SessionCreateRequest`, `SessionStateResponse`, etc.
   - Agent execution models: `AgentRunRequest`, `AgentRunResponse`
   - Parallel dispatch models: `DispatchConfig`, `StreamConfig`, `DispatchResponse`
   - Orchestration models: `AgentMetadata`, `PipelineStatus`, `ExecutionTraceResponse`
   - Rating models: `RubricCreateRequest`, `RatingResponse`, etc.

### Documentation
3. **`trends_and_insights_agent/API_DOCS.md`** (587 lines)
   - Comprehensive API documentation
   - All endpoints documented with examples
   - Usage patterns for single session, parallel dispatch, and ratings
   - JavaScript/TypeScript client examples
   - Implementation notes and best practices

### Testing
4. **`tests/test_api_server.py`** (393 lines)
   - Comprehensive test suite using pytest and FastAPI TestClient
   - Tests for all endpoint groups:
     - Session management (5 tests)
     - Agent execution (1 test)
     - Orchestration (3 tests)
     - Ratings (6 tests)
     - Health check (1 test)

### Infrastructure
5. **`run_api_server.sh`**
   - Convenience script to start the API server
   - Environment variable validation
   - Clear error messages for missing config

6. **`.env.example`**
   - Template for required environment variables
   - Documentation for optional variables

## API Endpoints Implemented

### Session Management (4 endpoints)
- `POST /api/v1/sessions` - Create session with optional preset
- `GET /api/v1/sessions/{session_id}/state` - Get full session state
- `PATCH /api/v1/sessions/{session_id}/state` - Update specific state keys
- `GET /api/v1/sessions/{session_id}/artifacts` - List session artifacts

### Agent Execution (2 endpoints)
- `POST /api/v1/run` - Send message to agent
- `GET /api/v1/run/{session_id}/stream` - SSE stream for agent execution

### Parallel Dispatch (3 endpoints)
- `POST /api/v1/dispatch` - Create parallel dispatch with cloned agents
- `GET /api/v1/dispatch/{dispatch_id}/stream` - Multiplexed SSE stream
- `DELETE /api/v1/dispatch/{dispatch_id}/{stream_id}` - Cancel stream

### Orchestration (3 endpoints)
- `GET /api/v1/orchestration/status` - All active pipelines
- `GET /api/v1/orchestration/{session_id}/trace` - Execution trace
- `GET /api/v1/orchestration/agents` - Agent hierarchy metadata

### Trends (2 endpoints)
- `POST /api/v1/trends/auto-select` - Auto-select trends (placeholder)
- `GET /api/v1/trends/available` - Get available trends (placeholder)

### Ratings (5 endpoints)
- `POST /api/v1/rubrics` - Create/update rubric
- `GET /api/v1/rubrics` - List all rubrics
- `GET /api/v1/rubrics/{rubric_id}` - Get specific rubric
- `POST /api/v1/ratings` - Submit rating
- `GET /api/v1/ratings` - Get ratings (filterable by session, artifact, rubric)

### Utility (1 endpoint)
- `GET /health` - Health check with system stats

**Total: 20 endpoints**

## Key Features

### 1. Agent Cloning for Parallel Dispatch
Uses ADK's `agent.clone()` method to create deep copies of the root agent, enabling:
- Multiple trend configurations running simultaneously
- Independent session state per stream
- Multiplexed SSE streaming for all parallel streams
- Individual stream cancellation

### 2. Enhanced SSE Streaming
- Standard SSE format: `data: {JSON}\n\n`
- Event types: `AgentStart`, `ModelResponse`, `ToolCall`, `Error`, `stream_complete`
- Execution trace tracking for all events
- Multiplexed streams with `stream_id` and `stream_name` metadata

### 3. In-Memory State Management
- Uses ADK's `InMemorySessionService` for session storage
- Global `AppState` class tracks:
  - Active dispatches and streams
  - Stream events for multiplexing
  - Execution traces per session
  - Pipeline statuses
  - Ratings and rubrics

### 4. Rating System
- Flexible rubric creation with weighted criteria
- Normalized scoring (0-1 scale) with custom ranges
- Ratings linked to session artifacts
- Queryable by session, artifact, or rubric
- Automatic weighted score calculation

### 5. CORS Support
Pre-configured for frontend dev servers:
- `http://localhost:5173` (Vite)
- `http://localhost:3000` (Create React App)
- `http://127.0.0.1:5173`
- `http://127.0.0.1:3000`

## Architecture Patterns

### Callback Integration
The API respects existing ADK callbacks:
- `_load_session_state` - Initializes session from presets
- `rate_limit_callback` - Throttles LLM API calls (1000 RPM default)
- `campaign_callback_function` - Sets default campaign state values

### Error Handling
- All endpoints wrapped in try/except
- HTTPException for client errors (400, 404)
- 500 errors for unexpected failures
- Full error logging with stack traces

### Data Models
All I/O validated with Pydantic:
- Request validation with detailed error messages
- Response serialization with datetime handling
- Type safety throughout the API

## Usage Example

```bash
# 1. Set environment variables
export BUCKET=my-gcs-bucket
export GOOGLE_CLOUD_PROJECT=my-project
export GOOGLE_CLOUD_PROJECT_NUMBER=123456789
export GOOGLE_CLOUD_LOCATION=us-central1
export YT_SECRET_MNGR_NAME=youtube-api-key
export GOOGLE_GENAI_USE_VERTEXAI=1

# 2. Start the API server
./run_api_server.sh

# 3. Access API docs
# Open browser to http://localhost:8000/docs
```

## Frontend Integration Points

The API is designed to support the following frontend features:

### Trend Configuration Interface (Task #3)
- `GET /api/v1/trends/available` - Fetch available trends
- `POST /api/v1/trends/auto-select` - Auto-select trends based on campaign
- `PATCH /api/v1/sessions/{session_id}/state` - Save selected trends

### Orchestration Dashboard (Task #4)
- `GET /api/v1/orchestration/status` - Real-time pipeline status
- `GET /api/v1/orchestration/{session_id}/trace` - Execution trace visualization
- `GET /api/v1/orchestration/agents` - Agent hierarchy diagram

### Rating Interface (Task #5)
- `GET /api/v1/rubrics` - Load available rubrics
- `POST /api/v1/rubrics` - Create custom rubrics
- `POST /api/v1/ratings` - Submit ratings
- `GET /api/v1/ratings?session_id={id}` - View ratings for a session

### AV Studio Interface (Task #6)
- `GET /api/v1/sessions/{session_id}/artifacts` - List video artifacts
- `GET /api/v1/sessions/{session_id}/state` - Get commercial_artifact key
- Artifacts stored in GCS at `gs://{bucket}/{gcs_folder}/`

### Parallel Execution
- `POST /api/v1/dispatch` - Run A/B tests with different trend configs
- `GET /api/v1/dispatch/{dispatch_id}/stream` - Monitor all streams
- Side-by-side comparison of results

## Testing

Run tests with:
```bash
poetry run pytest tests/test_api_server.py -v
```

All 16 tests pass:
- Session management: 5 tests
- Agent execution: 1 test
- Orchestration: 3 tests
- Ratings: 6 tests
- Health check: 1 test

## Next Steps

### For Frontend Developers

1. **Session Initialization**
   - Use `POST /api/v1/sessions` with `preset_config: "example_state_pixel"`
   - Store `session_id` in frontend state management (Redux/Zustand)

2. **SSE Client Setup**
   - Use `EventSource` API for SSE streams
   - Parse `event.data` as JSON
   - Handle `stream_complete` and `stream_error` events

3. **State Synchronization**
   - Poll `GET /api/v1/sessions/{session_id}/state` for updates
   - Use `PATCH` to update state from frontend (e.g., user selections)

4. **Artifact Display**
   - Fetch artifacts with `GET /api/v1/sessions/{session_id}/artifacts`
   - Download from GCS using artifact keys
   - Display images/videos in UI

### For Backend Developers

1. **Implement Trend Auto-Selection**
   - Complete `POST /api/v1/trends/auto-select`
   - Integrate with YouTube and Google Trends APIs
   - Use LLM to score trend relevance

2. **Implement Trend Fetching**
   - Complete `GET /api/v1/trends/available`
   - Cache results with TTL
   - Return structured trend data

3. **Add Session Persistence**
   - Replace `InMemorySessionService` with Firestore
   - Implement session cleanup/expiration
   - Add session recovery on server restart

4. **Add Authentication**
   - Integrate with Google Identity Platform
   - Add user management
   - Implement per-user rate limiting

5. **Add Monitoring**
   - Integrate OpenTelemetry for traces
   - Add Prometheus metrics
   - Set up alerting for errors

## Dependencies

Already available in `pyproject.toml`:
- `fastapi` (0.123.10)
- `uvicorn` (0.40.0)
- `google-adk` (^1.22.1)
- `google-genai` (^1.19.0)
- `pydantic` (via FastAPI)

No additional dependencies required.

## File Locations

All backend files in the worktree:
```
/usr/local/google/home/jwortz/zghost/.claude/worktrees/frontend-workflow/
├── trends_and_insights_agent/
│   ├── api_server.py                    # Main FastAPI app
│   ├── api_models.py                    # Pydantic schemas
│   └── API_DOCS.md                      # API documentation
├── tests/
│   └── test_api_server.py               # Test suite
├── run_api_server.sh                    # Start script
├── .env.example                         # Environment template
└── BACKEND_API_SUMMARY.md               # This file
```

## Notes

- The API server requires all environment variables to be set (see `.env.example`)
- Rate limiting is enforced via ADK's `rate_limit_callback` (default: 1000 RPM)
- Parallel dispatch respects the global rate limit across all streams
- Artifacts are stored in GCS under `{bucket}/{gcs_folder}/` (gcs_folder is timestamp-based)
- Session state follows the schema in `shared_libraries/schema_types.py`
- The root agent and all sub-agents are defined in `trends_and_insights_agent/agent.py`
