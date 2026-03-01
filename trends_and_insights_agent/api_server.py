"""
Extended API server for the marketing intelligence frontend.
Wraps ADK's runner with additional endpoints for parallel dispatch,
orchestration status, ratings, and enhanced streaming.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService, VertexAiSessionService
from google.genai import types

from .agent import root_agent
from . import eval_service
from .api_models import (
    AgentHierarchyResponse,
    AgentMetadata,
    AgentRunRequest,
    AgentRunResponse,
    ArtifactInfo,
    AvailableTrendsResponse,
    ConcurrencyConfigRequest,
    ConcurrencyStatusResponse,
    DispatchConfig,
    DispatchResponse,
    EvalRunRequest,
    EvalRunResponse,
    EvalSetInfo,
    EvalSetListResponse,
    ExecutionTraceResponse,
    NarrativePdfRequest,
    NarrativePdfResponse,
    NarrativeRefineRequest,
    NarrativeRefineResponse,
    OrchestrationStatusResponse,
    PipelineStatus,
    RatingListResponse,
    RatingResponse,
    RatingSubmitRequest,
    RubricCreateRequest,
    RubricListResponse,
    RubricResponse,
    SessionArtifactsResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionListResponse,
    SessionStateResponse,
    SessionStateUpdateRequest,
    SessionSummary,
    StreamEvent,
    TrendSafetyCheckRequest,
    TrendSafetyCheckResponse,
    TrendSafetyResult,
    StreamInfo,
    TraceEvent,
    TrendAutoSelectRequest,
    TrendAutoSelectResponse,
    TrendInfo,
)
from .shared_libraries.config import setup_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =====================================
# Global State Management
# =====================================


class AppState:
    """Global application state."""

    def __init__(self):
        self.session_service: Optional[InMemorySessionService] = None
        self.runner: Optional[InMemoryRunner] = None
        # Track active dispatches: dispatch_id -> List[StreamInfo]
        self.active_dispatches: Dict[str, List[StreamInfo]] = {}
        # Track stream tasks: stream_id -> asyncio.Task
        self.stream_tasks: Dict[str, asyncio.Task] = {}
        # Track stream events: stream_id -> List[Dict]
        self.stream_events: Dict[str, List[Dict]] = {}
        # Track execution traces: session_id -> List[TraceEvent]
        self.execution_traces: Dict[str, List[TraceEvent]] = {}
        # Track SSE events for replay: session_id -> List[Dict]
        self.session_sse_events: Dict[str, List[Dict]] = {}
        # Track pipeline statuses: session_id -> PipelineStatus
        self.pipeline_statuses: Dict[str, PipelineStatus] = {}
        # Ratings storage: rating_id -> RatingResponse
        self.ratings: Dict[str, RatingResponse] = {}
        # Rubrics storage: rubric_id -> RubricResponse
        self.rubrics: Dict[str, RubricResponse] = {}
        # Concurrency control
        self.max_concurrent_runs: int = 2
        self.run_semaphore: asyncio.Semaphore = asyncio.Semaphore(2)
        self.active_runs: Dict[str, str] = {}  # session_id -> user_id
        # Evaluation results storage: eval_id -> dict
        self.eval_results: Dict[str, dict] = {}


app_state = AppState()


def _create_session_service():
    """Create session service - VertexAI only when explicitly opted in.

    VertexAiSessionService requires app_name to be a ReasoningEngine resource
    name or ID, so it only works when deployed to Agent Engine. For local dev
    and Cloud Run, use InMemorySessionService.

    Set USE_VERTEX_SESSIONS=true and AGENT_ENGINE_ID=<engine-id> to enable.

    Environment variable resolution (highest priority first):
    - AGENT_ENGINE_ID (new unified variable)
    - MEMORY_BANK_AGENT_ENGINE_ID (deprecated)
    - VERTEX_SESSION_APP_NAME (deprecated)
    """
    use_vertex = os.environ.get("USE_VERTEX_SESSIONS", "").lower() == "true"
    if use_vertex:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        # Agent Engine sessions require us-central1 regardless of GOOGLE_CLOUD_LOCATION
        location = "us-central1"
        # Unified Agent Engine ID with backward compatibility
        engine_id = (
            os.environ.get("AGENT_ENGINE_ID")
            or os.environ.get("MEMORY_BANK_AGENT_ENGINE_ID")
            or os.environ.get("VERTEX_SESSION_APP_NAME")
        )
        if project and engine_id:
            try:
                svc = VertexAiSessionService(
                    project=project,
                    location=location,
                    agent_engine_id=engine_id,
                )
                logger.info(
                    f"Using VertexAiSessionService (project={project}, location={location}, agent_engine_id={engine_id})"
                )
                return svc
            except Exception as e:
                logger.warning(f"Failed to create VertexAiSessionService: {e}, falling back to InMemory")
    return InMemorySessionService()


# App name for session service — ReasoningEngine ID when using VertexAI, otherwise arbitrary string
# Unified Agent Engine ID with backward compatibility
SESSION_APP_NAME = (
    os.environ.get("AGENT_ENGINE_ID")
    or os.environ.get("MEMORY_BANK_AGENT_ENGINE_ID")
    or os.environ.get("VERTEX_SESSION_APP_NAME")
    or "trends_and_insights_agent"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    # Startup
    logger.info("Initializing ADK session service and runner...")
    app_state.runner = InMemoryRunner(
        agent=root_agent, app_name=SESSION_APP_NAME
    )
    # Override with custom session service if VertexAI sessions are enabled
    custom_session_service = _create_session_service()
    if not isinstance(custom_session_service, InMemorySessionService):
        logger.info("Overriding runner session service with custom VertexAiSessionService")
        app_state.runner.session_service = custom_session_service
    # Use the runner's session service so sessions are shared
    app_state.session_service = app_state.runner.session_service
    logger.info("API server ready")

    yield

    # Shutdown
    logger.info("Shutting down API server...")
    # Cancel all active stream tasks
    for task in app_state.stream_tasks.values():
        if not task.done():
            task.cancel()
    await asyncio.gather(*app_state.stream_tasks.values(), return_exceptions=True)
    logger.info("API server shutdown complete")


app = FastAPI(
    title="Marketing Intelligence API",
    description="Extended API for the ADK-based marketing intelligence agent system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================
# Helper Functions
# =====================================


def load_preset_config(preset_name: str) -> Dict[str, Any]:
    """Load a preset configuration from the profiles directory."""
    profiles_dir = os.path.join(
        os.path.dirname(__file__), "shared_libraries", "profiles"
    )
    preset_path = os.path.join(profiles_dir, f"{preset_name}.json")

    if not os.path.exists(preset_path):
        # Try without .json extension
        preset_path = os.path.join(profiles_dir, preset_name)

    if not os.path.exists(preset_path):
        raise HTTPException(
            status_code=404, detail=f"Preset configuration '{preset_name}' not found"
        )

    try:
        with open(preset_path, "r") as f:
            data = json.load(f)
            # Extract state if it's wrapped in a "state" key
            if "state" in data and isinstance(data["state"], dict):
                return data["state"]
            return data
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid JSON in preset configuration: {str(e)}"
        )


def format_event_for_sse(event: Any) -> Dict[str, Any]:
    """Format an ADK Event for SSE streaming.

    ADK 1.25.1 Event fields: content (Content with parts), author, actions,
    turn_complete, error_code, error_message, etc.
    """
    now_ms = int(time.time() * 1000)
    event_type = "agent_step"  # default

    event_data = {
        "type": event_type,
        "timestamp": now_ms,
        "data": {},
    }

    # Extract agent name from author field
    if hasattr(event, "author"):
        event_data["agent_name"] = event.author

    # Determine specific event type from content
    content = getattr(event, "content", None)
    has_function_call = False
    has_function_response = False
    has_text = False

    if content and hasattr(content, "parts") and content.parts:
        parts_data = []
        for part in content.parts:
            part_dict = {}
            if hasattr(part, "text") and part.text:
                part_dict["text"] = part.text
                has_text = True
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                part_dict["function_call"] = {
                    "name": getattr(fc, "name", "unknown"),
                    "args": getattr(fc, "args", {}),
                }
                event_data["tool_name"] = getattr(fc, "name", "")
                has_function_call = True
            if hasattr(part, "function_response") and part.function_response:
                fr = part.function_response
                part_dict["function_response"] = {
                    "name": getattr(fr, "name", "unknown"),
                    "response": getattr(fr, "response", {}),
                }
                has_function_response = True
            if part_dict:
                parts_data.append(part_dict)
        if parts_data:
            event_data["data"]["parts"] = parts_data

    # Handle errors
    if hasattr(event, "error_message") and event.error_message:
        event_data["data"]["error"] = event.error_message
        event_type = "error"
    elif has_function_call:
        event_type = "tool_call"
    elif has_function_response:
        event_type = "tool_response"
    elif getattr(event, "turn_complete", False):
        event_type = "agent_complete"
    elif has_text:
        event_type = "agent_step"

    event_data["type"] = event_type
    return event_data


async def stream_agent_events(
    runner: InMemoryRunner, session_id: str, user_id: str, message: str
) -> AsyncIterator[str]:
    """Stream SSE-formatted events from agent execution."""
    try:
        # Create user message content
        user_content = types.Content(
            role="user", parts=[types.Part(text=message)]
        )

        # Stream events from the runner
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=user_content
        ):
            # Format event for SSE
            event_data = format_event_for_sse(event)
            logger.info(f"SSE event: agent={event_data.get('agent_name','?')} type={event_data.get('type','?')}")

            # Track event in execution trace
            if session_id not in app_state.execution_traces:
                app_state.execution_traces[session_id] = []

            trace_event = TraceEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                agent_name=event_data.get("agent_name", "unknown"),
                event_type=event_data.get("type", "unknown"),
                details=event_data.get("data", {}),
                parent_event_id=None,
            )
            app_state.execution_traces[session_id].append(trace_event)

            # Store raw SSE event for frontend replay
            if session_id not in app_state.session_sse_events:
                app_state.session_sse_events[session_id] = []
            app_state.session_sse_events[session_id].append(event_data)

            # Yield SSE-formatted event
            yield f"data: {json.dumps(event_data)}\n\n"

        # Send completion event
        completion_event = {
            "type": "agent_complete",
            "timestamp": int(time.time() * 1000),
            "session_id": session_id,
            "agent_name": "root_agent",
        }
        # Store completion event for polling-based detection
        if session_id not in app_state.session_sse_events:
            app_state.session_sse_events[session_id] = []
        app_state.session_sse_events[session_id].append(completion_event)
        yield f"data: {json.dumps(completion_event)}\n\n"

    except Exception as e:
        logger.error(f"Error in stream_agent_events: {str(e)}", exc_info=True)
        error_event = {
            "type": "error",
            "timestamp": int(time.time() * 1000),
            "error": str(e),
        }
        yield f"data: {json.dumps(error_event)}\n\n"


async def run_parallel_stream(
    stream_id: str, stream_name: str, cloned_agent, session_id: str, user_id: str
):
    """Run a single parallel stream and collect events."""
    try:
        logger.info(f"Starting parallel stream: {stream_name} (stream_id={stream_id})")

        # Update stream status
        for streams in app_state.active_dispatches.values():
            for stream_info in streams:
                if stream_info.stream_id == stream_id:
                    stream_info.status = "running"

        # Initialize event storage for this stream
        app_state.stream_events[stream_id] = []

        # Create a runner for this cloned agent
        runner = InMemoryRunner(agent=cloned_agent)

        # Run the agent (this will trigger initial state loading via callbacks)
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[
                    types.Part(text=
                        f"Stream '{stream_name}' initialized. Ready to process trends."
                    )
                ],
            ),
        ):
            # Format and store event
            event_data = format_event_for_sse(event)
            app_state.stream_events[stream_id].append(
                {
                    "stream_id": stream_id,
                    "stream_name": stream_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "event": event_data,
                }
            )

        # Mark stream as completed
        for streams in app_state.active_dispatches.values():
            for stream_info in streams:
                if stream_info.stream_id == stream_id:
                    stream_info.status = "completed"

        logger.info(f"Completed parallel stream: {stream_name} (stream_id={stream_id})")

    except asyncio.CancelledError:
        logger.info(f"Stream {stream_name} cancelled")
        for streams in app_state.active_dispatches.values():
            for stream_info in streams:
                if stream_info.stream_id == stream_id:
                    stream_info.status = "cancelled"
        raise

    except Exception as e:
        logger.error(f"Error in parallel stream {stream_name}: {str(e)}", exc_info=True)
        for streams in app_state.active_dispatches.values():
            for stream_info in streams:
                if stream_info.stream_id == stream_id:
                    stream_info.status = "failed"


# =====================================
# Session Management Endpoints
# =====================================


@app.get("/api/v1/sessions", response_model=SessionListResponse)
async def list_sessions(user_id: str = Query(default="default-user")):
    """List all sessions from the session service with metadata summaries."""
    try:
        result = await app_state.session_service.list_sessions(
            app_name=SESSION_APP_NAME, user_id=user_id
        )

        summaries: list[SessionSummary] = []
        for session in result.sessions:
            try:
                state = session.state or {}

                # Determine pipeline status from state
                status = None
                if state.get("commercial_artifact"):
                    status = "completed"
                elif state.get("final_select_ad_copies"):
                    status = "ad_creative_done"
                elif state.get("combined_final_cited_report"):
                    status = "research_done"
                elif state.get("target_search_trends") or state.get("target_yt_trends"):
                    status = "trends_selected"

                # Count media artifacts
                img_keys = state.get("img_artifact_keys", {})
                vid_keys = state.get("vid_artifact_keys", {})
                img_list = img_keys.get("img_artifact_keys", []) if isinstance(img_keys, dict) else []
                vid_list = vid_keys.get("vid_artifact_keys", []) if isinstance(vid_keys, dict) else []

                summaries.append(
                    SessionSummary(
                        session_id=session.id,
                        user_id=session.user_id,
                        last_update_time=session.last_update_time,
                        brand=state.get("brand"),
                        target_product=state.get("target_product"),
                        target_audience=state.get("target_audience"),
                        commercial_duration=state.get("commercial_duration"),
                        autopilot_mode=state.get("autopilot_mode"),
                        status=status,
                        has_report=bool(state.get("combined_final_cited_report")),
                        has_commercial=bool(state.get("commercial_artifact")),
                        has_images=len(img_list) > 0,
                        has_videos=len(vid_list) > 0,
                        image_count=len(img_list),
                        video_count=len(vid_list),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping malformed session {getattr(session, 'id', 'unknown')}: {e}")
                continue

        # Sort by last_update_time descending (most recent first)
        summaries.sort(key=lambda s: s.last_update_time, reverse=True)

        return SessionListResponse(sessions=summaries, total=len(summaries))

    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@app.post("/api/v1/sessions", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new session with optional preset configuration."""
    try:
        user_id = "default-user"

        # Load preset config if specified
        initial_state = {}
        if request.preset_config:
            initial_state = load_preset_config(request.preset_config)
        elif request.initial_state:
            initial_state = request.initial_state

        # Merge with default state structure
        default_state = setup_config.empty_session_state.get("state", {})
        merged_state = {**default_state, **initial_state}

        # Create session with state included
        # Note: VertexAiSessionService generates its own session IDs and will
        # reject user-provided session_id. InMemorySessionService requires it.
        if isinstance(app_state.session_service, VertexAiSessionService):
            # Let VertexAI generate the session ID
            session = await app_state.session_service.create_session(
                user_id=user_id,
                app_name=SESSION_APP_NAME,
                state=merged_state,
            )
            session_id = session.id
        else:
            # InMemorySessionService requires session_id parameter
            session_id = str(uuid.uuid4())
            await app_state.session_service.create_session(
                session_id=session_id,
                user_id=user_id,
                app_name=SESSION_APP_NAME,
                state=merged_state,
            )

        # Best-effort: pre-load relevant memories from past campaigns
        if merged_state.get("brand") or merged_state.get("target_product"):
            try:
                import aiohttp
                query = f"{merged_state.get('brand', '')} {merged_state.get('target_product', '')}"
                scope = {"app_name": "trends_and_insights_agent", "user_id": user_id}
                async with aiohttp.ClientSession() as http_session:
                    resp = await http_session.post(
                        "http://localhost:8082/api/memories/retrieve",
                        json={"scope": scope, "query": query.strip()},
                        timeout=aiohttp.ClientTimeout(total=5),
                    )
                    if resp.status == 200:
                        data = await resp.json()
                        memories = data.get("memories", [])
                        if memories:
                            session_obj = await app_state.session_service.get_session(
                                session_id=session_id,
                                user_id=user_id,
                                app_name=SESSION_APP_NAME,
                            )
                            if session_obj:
                                session_obj.state["prior_campaign_insights"] = memories
                                logger.info(f"Pre-loaded {len(memories)} prior insights for {query}")
            except Exception as e:
                logger.warning(f"Failed to pre-load memories: {e}")

        # Get Agent Engine ID from environment if available
        agent_engine_id = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
        is_vertex_session = isinstance(app_state.session_service, VertexAiSessionService)

        return SessionCreateResponse(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            agent_engine_id=agent_engine_id,
            is_vertex_session=is_vertex_session,
        )

    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.get("/api/v1/sessions/{session_id}/state", response_model=SessionStateResponse)
async def get_session_state(session_id: str, user_id: str = Query(default="default-user")):
    """Get full session state."""
    try:
        session = await app_state.session_service.get_session(
            session_id=session_id, user_id=user_id, app_name=SESSION_APP_NAME
        )
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return SessionStateResponse(
            session_id=session_id, state=dict(session.state)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session state: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get session state: {str(e)}"
        )


@app.patch("/api/v1/sessions/{session_id}/state")
async def update_session_state(
    session_id: str, request: SessionStateUpdateRequest, user_id: str = Query(default="default-user")
):
    """Update specific session state keys."""
    try:
        session = await app_state.session_service.get_session(
            session_id=session_id, user_id=user_id, app_name=SESSION_APP_NAME
        )
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Update state keys
        for key, value in request.updates.items():
            session.state[key] = value

        return {"status": "success", "updated_keys": list(request.updates.keys())}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session state: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update session state: {str(e)}"
        )


@app.get("/api/v1/sessions/{session_id}/artifacts", response_model=SessionArtifactsResponse)
async def get_session_artifacts(
    session_id: str, user_id: str = Query(default="default-user")
):
    """List artifacts for a session."""
    try:
        session = await app_state.session_service.get_session(
            session_id=session_id, user_id=user_id, app_name=SESSION_APP_NAME
        )
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract artifact information from session state
        artifacts = []
        state_dict = dict(session.state)

        # Check for image artifacts
        if "img_artifact_keys" in state_dict:
            img_keys = state_dict.get("img_artifact_keys", {})
            if isinstance(img_keys, dict):
                img_keys = img_keys.get("img_artifact_keys", [])
            for key in img_keys:
                artifacts.append(
                    ArtifactInfo(
                        key=key,
                        version=1,
                        mime_type="image/png",
                        size_bytes=None,
                        created_at=None,
                    )
                )

        # Check for video artifacts
        if "vid_artifact_keys" in state_dict:
            vid_keys = state_dict.get("vid_artifact_keys", {})
            if isinstance(vid_keys, dict):
                vid_keys = vid_keys.get("vid_artifact_keys", [])
            for key in vid_keys:
                artifacts.append(
                    ArtifactInfo(
                        key=key,
                        version=1,
                        mime_type="video/mp4",
                        size_bytes=None,
                        created_at=None,
                    )
                )

        # Check for commercial artifact
        if state_dict.get("commercial_artifact"):
            artifacts.append(
                ArtifactInfo(
                    key="commercial_artifact",
                    version=1,
                    mime_type="video/mp4",
                    size_bytes=None,
                    created_at=None,
                )
            )

        return SessionArtifactsResponse(session_id=session_id, artifacts=artifacts)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session artifacts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get session artifacts: {str(e)}"
        )


# =====================================
# Agent Execution Endpoints
# =====================================


@app.post("/api/v1/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest):
    """Send message to agent and get stream URL."""
    try:
        # Use provided session_id or create new one
        session_id = request.session_id or str(uuid.uuid4())
        user_id = request.user_id or "default-user"

        # Create session if it doesn't exist
        try:
            await app_state.session_service.get_session(
                session_id=session_id, user_id=user_id, app_name=SESSION_APP_NAME
            )
        except:
            await app_state.session_service.create_session(
                session_id=session_id, user_id=user_id
            )

        # Return stream URL
        stream_url = f"/api/v1/run/{session_id}/stream?user_id={user_id}&message={request.message}"

        return AgentRunResponse(
            session_id=session_id, user_id=user_id, stream_url=stream_url
        )

    except Exception as e:
        logger.error(f"Error running agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run agent: {str(e)}")


async def stream_with_concurrency_control(
    runner: InMemoryRunner, session_id: str, user_id: str, message: str
) -> AsyncIterator[str]:
    """Wrapper generator that enforces concurrency control via semaphore."""
    # Check if we need to queue
    if app_state.run_semaphore.locked():
        queued_event = {
            "type": "queued",
            "timestamp": int(time.time() * 1000),
            "session_id": session_id,
            "message": "Pipeline queued, waiting for available slot...",
        }
        logger.info(f"Session {session_id} queued (waiting for semaphore)")
        yield f"data: {json.dumps(queued_event)}\n\n"

    # Acquire semaphore (blocks if at capacity)
    async with app_state.run_semaphore:
        # Track this run
        app_state.active_runs[session_id] = user_id
        logger.info(
            f"Session {session_id} acquired semaphore "
            f"({len(app_state.active_runs)}/{app_state.max_concurrent_runs} active)"
        )

        try:
            # Stream all events from the wrapped generator
            async for event_data in stream_agent_events(runner, session_id, user_id, message):
                yield event_data
        finally:
            # Release tracking
            app_state.active_runs.pop(session_id, None)
            logger.info(
                f"Session {session_id} released semaphore "
                f"({len(app_state.active_runs)}/{app_state.max_concurrent_runs} active)"
            )


@app.get("/api/v1/run/{session_id}/stream")
async def stream_agent_run(
    session_id: str, user_id: str = Query(default="default-user"), message: str = Query(...)
):
    """SSE stream for agent execution."""
    return StreamingResponse(
        stream_with_concurrency_control(app_state.runner, session_id, user_id, message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =====================================
# Concurrency Control Endpoints
# =====================================


@app.get("/api/v1/concurrency/status", response_model=ConcurrencyStatusResponse)
async def get_concurrency_status():
    """Get current concurrency status."""
    try:
        active_count = len(app_state.active_runs)
        # Calculate queued count: this is approximate, as we can't directly query semaphore waiters
        # We use the semaphore's locked state as a proxy
        queued_count = 0
        if app_state.run_semaphore.locked():
            # If semaphore is locked, there might be queued requests
            # This is a conservative estimate
            queued_count = max(0, active_count - app_state.max_concurrent_runs)

        return ConcurrencyStatusResponse(
            active_count=active_count,
            max_concurrent=app_state.max_concurrent_runs,
            queued_count=queued_count,
        )
    except Exception as e:
        logger.error(f"Error getting concurrency status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get concurrency status: {str(e)}"
        )


@app.patch("/api/v1/concurrency/config")
async def update_concurrency_config(request: ConcurrencyConfigRequest):
    """Update concurrency configuration."""
    try:
        old_max = app_state.max_concurrent_runs
        new_max = request.max_concurrent

        # Update max concurrent
        app_state.max_concurrent_runs = new_max

        # Recreate semaphore with new limit
        # Note: This recreates the semaphore, which means any current waiters
        # will continue waiting on the old semaphore. New requests will use the new one.
        # For a production system, you might want a more sophisticated migration strategy.
        app_state.run_semaphore = asyncio.Semaphore(new_max)

        logger.info(f"Updated concurrency limit: {old_max} -> {new_max}")

        return {
            "status": "updated",
            "old_max_concurrent": old_max,
            "new_max_concurrent": new_max,
            "active_count": len(app_state.active_runs),
        }
    except Exception as e:
        logger.error(f"Error updating concurrency config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update concurrency config: {str(e)}"
        )


# =====================================
# Evaluation Endpoints
# =====================================


@app.post("/api/v1/eval/run", response_model=EvalRunResponse)
async def run_evaluation(request: EvalRunRequest):
    """Run an ADK evaluation with optional custom rubric criteria."""
    try:
        # Generate eval ID
        eval_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # Convert Pydantic models to dicts for eval_service
        rubric_criteria = None
        if request.rubric_criteria:
            rubric_criteria = [
                {
                    "name": criterion.name,
                    "description": criterion.description,
                    "weight": criterion.weight,
                }
                for criterion in request.rubric_criteria
            ]

        # Initialize result entry
        app_state.eval_results[eval_id] = {
            "eval_id": eval_id,
            "status": "running",
            "results": None,
            "started_at": started_at,
            "completed_at": None,
            "eval_set_path": request.eval_set_path,
            "agent_module": request.agent_module,
            "rubric_criteria": rubric_criteria,
        }

        # Run evaluation asynchronously in background
        async def run_eval_async():
            try:
                results = eval_service.run_evaluation(
                    eval_dataset_path=request.eval_set_path,
                    agent_module=request.agent_module,
                    rubric_criteria=rubric_criteria,
                )
                app_state.eval_results[eval_id]["status"] = "completed"
                app_state.eval_results[eval_id]["results"] = results
                app_state.eval_results[eval_id]["completed_at"] = datetime.utcnow()
                logger.info(f"Evaluation {eval_id} completed successfully")
            except Exception as e:
                logger.error(f"Evaluation {eval_id} failed: {str(e)}", exc_info=True)
                app_state.eval_results[eval_id]["status"] = "failed"
                app_state.eval_results[eval_id]["error"] = str(e)
                app_state.eval_results[eval_id]["completed_at"] = datetime.utcnow()

        # Start background task
        asyncio.create_task(run_eval_async())

        return EvalRunResponse(
            eval_id=eval_id,
            status="running",
            results=None,
            started_at=started_at,
            completed_at=None,
        )

    except Exception as e:
        logger.error(f"Error starting evaluation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to start evaluation: {str(e)}"
        )


@app.get("/api/v1/eval/sets", response_model=EvalSetListResponse)
async def list_eval_sets(eval_dir: str = Query(default="tests")):
    """List available evaluation datasets."""
    try:
        eval_sets = eval_service.list_eval_sets(eval_dir=eval_dir)
        eval_set_infos = [
            EvalSetInfo(
                name=es["name"],
                path=es["path"],
                num_cases=es["num_cases"],
            )
            for es in eval_sets
        ]
        return EvalSetListResponse(eval_sets=eval_set_infos)
    except Exception as e:
        logger.error(f"Error listing eval sets: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list eval sets: {str(e)}"
        )


@app.get("/api/v1/eval/sets/{eval_set_name}")
async def get_eval_set(eval_set_name: str, eval_dir: str = Query(default="tests")):
    """Get the content of a specific evaluation dataset."""
    try:
        # Construct path from name (add .test.json if not present)
        if not eval_set_name.endswith(".test.json"):
            eval_set_name = f"{eval_set_name}.test.json"

        eval_path = f"{eval_dir}/{eval_set_name}"
        content = eval_service.load_eval_set(eval_path)

        return {
            "name": eval_set_name,
            "path": eval_path,
            "content": content,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading eval set: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to load eval set: {str(e)}"
        )


@app.get("/api/v1/eval/results/{eval_id}", response_model=EvalRunResponse)
async def get_eval_results(eval_id: str):
    """Get the results of a specific evaluation run."""
    try:
        if eval_id not in app_state.eval_results:
            raise HTTPException(status_code=404, detail=f"Evaluation {eval_id} not found")

        eval_data = app_state.eval_results[eval_id]
        return EvalRunResponse(
            eval_id=eval_data["eval_id"],
            status=eval_data["status"],
            results=eval_data.get("results"),
            started_at=eval_data["started_at"],
            completed_at=eval_data.get("completed_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching eval results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch eval results: {str(e)}"
        )


# =====================================
# Parallel Dispatch Endpoints
# =====================================


@app.post("/api/v1/dispatch", response_model=DispatchResponse)
async def dispatch_parallel(request: DispatchConfig):
    """Clone agent and run multiple configs in parallel."""
    try:
        dispatch_id = str(uuid.uuid4())
        streams = []
        user_id = "default-user"

        # Limit parallelism
        max_parallel = request.max_parallel or len(request.streams)

        for stream_config in request.streams:
            # Generate IDs
            stream_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())

            # Clone the root agent with a unique name
            cloned_agent = root_agent.clone(
                update={"name": f"stream_{stream_config.name}"}
            )

            # Create session
            await app_state.session_service.create_session(
                session_id=session_id, user_id=user_id
            )

            # Apply trend config to session state
            session = await app_state.session_service.get_session(
                session_id=session_id, user_id=user_id, app_name=SESSION_APP_NAME
            )

            # Load preset if specified
            if stream_config.session_preset:
                preset_state = load_preset_config(stream_config.session_preset)
                for key, value in preset_state.items():
                    session.state[key] = value

            # Apply trend config
            for key, value in stream_config.trend_config.items():
                session.state[key] = value

            # Create stream info
            stream_info = StreamInfo(
                stream_id=stream_id,
                stream_name=stream_config.name,
                session_id=session_id,
                status="pending",
                created_at=datetime.utcnow(),
            )
            streams.append(stream_info)

            # Start async execution
            task = asyncio.create_task(
                run_parallel_stream(stream_id, stream_config.name, cloned_agent, session_id, user_id)
            )
            app_state.stream_tasks[stream_id] = task

        # Store dispatch info
        app_state.active_dispatches[dispatch_id] = streams

        # Return response
        stream_url = f"/api/v1/dispatch/{dispatch_id}/stream"
        return DispatchResponse(
            dispatch_id=dispatch_id, streams=streams, stream_url=stream_url
        )

    except Exception as e:
        logger.error(f"Error dispatching parallel streams: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to dispatch parallel streams: {str(e)}"
        )


@app.get("/api/v1/dispatch/{dispatch_id}/stream")
async def stream_multiplexed_dispatch(dispatch_id: str):
    """Multiplexed SSE stream for all parallel streams in a dispatch."""

    async def generate_multiplexed_events():
        try:
            if dispatch_id not in app_state.active_dispatches:
                error_event = {
                    "type": "error",
                    "error": f"Dispatch {dispatch_id} not found",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                return

            streams = app_state.active_dispatches[dispatch_id]
            stream_ids = [s.stream_id for s in streams]

            # Track last sent event index for each stream
            last_sent_indices = {sid: 0 for sid in stream_ids}

            # Poll for new events from all streams
            while True:
                all_completed = True
                any_events_sent = False

                for stream_id in stream_ids:
                    # Check stream status
                    stream_info = next(
                        (s for s in streams if s.stream_id == stream_id), None
                    )
                    if stream_info and stream_info.status not in [
                        "completed",
                        "failed",
                        "cancelled",
                    ]:
                        all_completed = False

                    # Get new events for this stream
                    if stream_id in app_state.stream_events:
                        events = app_state.stream_events[stream_id]
                        start_idx = last_sent_indices[stream_id]

                        for event in events[start_idx:]:
                            yield f"data: {json.dumps(event)}\n\n"
                            any_events_sent = True
                            last_sent_indices[stream_id] += 1

                # If all streams completed, send final event and exit
                if all_completed:
                    completion_event = {
                        "type": "dispatch_complete",
                        "dispatch_id": dispatch_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "streams": [
                            {
                                "stream_id": s.stream_id,
                                "stream_name": s.stream_name,
                                "status": s.status,
                            }
                            for s in streams
                        ],
                    }
                    yield f"data: {json.dumps(completion_event)}\n\n"
                    break

                # Small delay between polls if no events
                if not any_events_sent:
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in multiplexed stream: {str(e)}", exc_info=True)
            error_event = {
                "type": "stream_error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        generate_multiplexed_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/api/v1/dispatch/{dispatch_id}/{stream_id}")
async def cancel_stream(dispatch_id: str, stream_id: str):
    """Cancel a specific stream in a dispatch."""
    try:
        if dispatch_id not in app_state.active_dispatches:
            raise HTTPException(status_code=404, detail=f"Dispatch {dispatch_id} not found")

        if stream_id not in app_state.stream_tasks:
            raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")

        # Cancel the task
        task = app_state.stream_tasks[stream_id]
        if not task.done():
            task.cancel()

        # Update stream status
        for stream_info in app_state.active_dispatches[dispatch_id]:
            if stream_info.stream_id == stream_id:
                stream_info.status = "cancelled"

        return {"status": "success", "stream_id": stream_id, "action": "cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling stream: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel stream: {str(e)}")


# =====================================
# Orchestration Endpoints
# =====================================


@app.get("/api/v1/orchestration/status", response_model=OrchestrationStatusResponse)
async def get_orchestration_status():
    """Get status of all active pipelines."""
    try:
        active_pipelines = list(app_state.pipeline_statuses.values())
        total_sessions = len(set(p.session_id for p in active_pipelines))

        return OrchestrationStatusResponse(
            active_pipelines=active_pipelines, total_sessions=total_sessions
        )

    except Exception as e:
        logger.error(f"Error getting orchestration status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get orchestration status: {str(e)}"
        )


@app.get("/api/v1/orchestration/{session_id}/trace", response_model=ExecutionTraceResponse)
async def get_execution_trace(session_id: str):
    """Get execution trace for a session."""
    try:
        events = app_state.execution_traces.get(session_id, [])

        return ExecutionTraceResponse(
            session_id=session_id, events=events, total_events=len(events)
        )

    except Exception as e:
        logger.error(f"Error getting execution trace: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get execution trace: {str(e)}"
        )


@app.get("/api/v1/orchestration/{session_id}/events")
async def get_session_events(session_id: str):
    """Get stored SSE events for a session (for frontend replay/hydration)."""
    events = app_state.session_sse_events.get(session_id, [])
    return {"session_id": session_id, "events": events, "total_events": len(events)}


# =====================================
# Event Reconstruction from Session State
# =====================================

# Phase definitions: (phase_name, trigger_key, agents_to_synthesize)
_RECONSTRUCTION_PHASES = [
    (
        "trend_discovery",
        ["target_search_trends", "target_yt_trends"],
        ["trends_and_insights_agent"],
    ),
    (
        "research",
        ["combined_final_cited_report"],
        ["research_orchestrator", "combined_research_pipeline", "combined_report_composer"],
    ),
    (
        "ad_copy",
        ["final_select_ad_copies"],
        ["ad_content_generator_agent", "ad_copy_drafter", "ad_copy_critic"],
    ),
    (
        "visual_concepts",
        ["final_select_vis_concepts"],
        ["visual_concept_drafter", "visual_concept_critic", "visual_concept_finalizer"],
    ),
    (
        "media_generation",
        ["img_artifact_keys", "vid_artifact_keys"],
        ["visual_generator"],
    ),
    (
        "commercial",
        ["commercial_artifact"],
        ["av_editing_studio_agent"],
    ),
    (
        "focus_group",
        ["focus_group_evaluation"],
        ["focus_group_evaluator_agent"],
    ),
]

# Estimated relative duration weights per phase (must sum to ~1.0)
_PHASE_WEIGHTS = {
    "trend_discovery": 0.05,
    "research": 0.35,
    "ad_copy": 0.10,
    "visual_concepts": 0.10,
    "media_generation": 0.20,
    "commercial": 0.15,
    "focus_group": 0.05,
}


def _unwrap_state_value(value: Any, key: str) -> Any:
    """Unwrap session state values that use the {key: actual_value} pattern.

    Many session state keys store data as {"key_name": [actual list]} rather
    than a bare list. This helper unwraps that pattern.
    """
    if isinstance(value, dict) and key in value:
        return value[key]
    return value


def _extract_phase_content(phase_name: str, state: Dict[str, Any]) -> List[str]:
    """Extract human-readable content snippets for a phase from session state."""
    snippets = []

    if phase_name == "trend_discovery":
        brand = state.get("brand", "Unknown brand")
        product = state.get("target_product", "Unknown product")
        audience = state.get("target_audience", "")
        snippets.append(f"Campaign setup: {brand} — {product}")
        if audience:
            aud_preview = audience[:150] + "..." if len(str(audience)) > 150 else str(audience)
            snippets.append(f"Target audience: {aud_preview}")
        # Selected trends — unwrap {"target_search_trends": [...]} pattern
        raw_search = state.get("target_search_trends", [])
        raw_yt = state.get("target_yt_trends", [])
        search_trends = _unwrap_state_value(raw_search, "target_search_trends")
        yt_trends = _unwrap_state_value(raw_yt, "target_yt_trends")
        if not isinstance(search_trends, list):
            search_trends = []
        if not isinstance(yt_trends, list):
            yt_trends = []
        trend_titles = []
        for t in search_trends[:3]:
            title = t.get("trend_title", t.get("title", str(t))) if isinstance(t, dict) else str(t)
            trend_titles.append(title)
        for t in yt_trends[:3]:
            title = t.get("video_title", t.get("title", str(t))) if isinstance(t, dict) else str(t)
            trend_titles.append(title)
        if trend_titles:
            snippets.append(f"Selected trends: {', '.join(trend_titles)}")

    elif phase_name == "research":
        report = state.get("combined_final_cited_report", "")
        if report:
            preview = str(report)[:300]
            snippets.append(f"{preview}...")
            snippets.append("View full report in Narrative tab.")

    elif phase_name == "ad_copy":
        raw_copies = state.get("final_select_ad_copies", [])
        copies = _unwrap_state_value(raw_copies, "final_select_ad_copies")
        if isinstance(copies, list):
            for copy in copies[:3]:
                if isinstance(copy, dict):
                    headline = copy.get("headline", copy.get("title", ""))
                    if headline:
                        snippets.append(f"Ad copy: {headline}")
                elif isinstance(copy, str):
                    snippets.append(f"Ad copy: {copy[:100]}")

    elif phase_name == "visual_concepts":
        raw_concepts = state.get("final_select_vis_concepts", [])
        concepts = _unwrap_state_value(raw_concepts, "final_select_vis_concepts")
        if isinstance(concepts, list):
            for concept in concepts[:3]:
                if isinstance(concept, dict):
                    name = concept.get("concept_name", concept.get("name", ""))
                    if name:
                        snippets.append(f"Visual concept: {name}")

    elif phase_name == "media_generation":
        img_keys = state.get("img_artifact_keys", {})
        vid_keys = state.get("vid_artifact_keys", {})
        img_list = img_keys.get("img_artifact_keys", []) if isinstance(img_keys, dict) else []
        vid_list = vid_keys.get("vid_artifact_keys", []) if isinstance(vid_keys, dict) else []
        snippets.append(f"Generated {len(img_list)} images and {len(vid_list)} videos.")
        snippets.append("View media in Results tab.")

    elif phase_name == "commercial":
        artifact = state.get("commercial_artifact", "")
        duration = state.get("commercial_duration", 30)
        if isinstance(artifact, dict):
            key = artifact.get("artifact_key", "commercial")
            snippets.append(f"{duration}s commercial produced: {key}")
        else:
            snippets.append(f"{duration}s commercial produced.")

    elif phase_name == "focus_group":
        evaluation = state.get("focus_group_evaluation", "")
        if isinstance(evaluation, str) and evaluation:
            preview = evaluation[:300]
            snippets.append(f"Focus group evaluation: {preview}...")
        elif isinstance(evaluation, dict):
            summary = evaluation.get("summary", evaluation.get("overall", ""))
            if summary:
                snippets.append(f"Focus group: {str(summary)[:300]}")

    return snippets if snippets else [f"{phase_name.replace('_', ' ').title()} completed."]


def _reconstruct_events_from_state(
    session_id: str,
    state: Dict[str, Any],
    last_update_time: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Synthesize AgentEvent dicts from session state keys.

    Detects which pipeline phases completed based on state key presence,
    then generates synthetic events matching the live SSE event format.
    """
    events: List[Dict[str, Any]] = []

    # Determine time anchors
    gcs_folder = state.get("gcs_folder", "")
    start_ts = None
    if gcs_folder:
        try:
            # Format: 2025_03_01_14_30
            dt = datetime.strptime(gcs_folder, "%Y_%m_%d_%H_%M")
            start_ts = dt.timestamp() * 1000
        except ValueError:
            pass

    if start_ts is None:
        # Fallback: use last_update_time minus 20 minutes
        if last_update_time:
            start_ts = last_update_time * 1000 - 20 * 60 * 1000
        else:
            start_ts = time.time() * 1000 - 20 * 60 * 1000

    end_ts = (last_update_time * 1000) if last_update_time else time.time() * 1000
    total_duration = max(end_ts - start_ts, 60_000)  # at least 1 minute

    # Detect completed phases
    completed_phases = []
    for phase_name, trigger_keys, agents in _RECONSTRUCTION_PHASES:
        has_trigger = any(
            state.get(key) not in (None, "", [], {})
            for key in trigger_keys
        )
        if has_trigger:
            completed_phases.append((phase_name, agents))

    if not completed_phases:
        return []

    # Compute cumulative time offsets for each completed phase
    total_weight = sum(_PHASE_WEIGHTS.get(p, 0.1) for p, _ in completed_phases)
    current_offset = 0.0

    for phase_name, agents in completed_phases:
        weight = _PHASE_WEIGHTS.get(phase_name, 0.1)
        phase_duration = total_duration * (weight / total_weight)
        phase_start = start_ts + current_offset
        phase_end = phase_start + phase_duration

        content_snippets = _extract_phase_content(phase_name, state)

        # Generate events for this phase
        # Event 1: agent_start for the primary agent
        primary_agent = agents[0]
        events.append({
            "type": "agent_start",
            "agent_name": primary_agent,
            "timestamp": int(phase_start),
            "data": {
                "parts": [{"text": f"Starting {phase_name.replace('_', ' ')}..."}],
            },
        })

        # Event 2+: agent_step events with content for each sub-agent
        num_steps = len(agents)
        for i, agent_name in enumerate(agents):
            step_ts = int(phase_start + (phase_duration * (i + 1) / (num_steps + 1)))
            snippet = content_snippets[i] if i < len(content_snippets) else ""
            if snippet:
                events.append({
                    "type": "agent_step",
                    "agent_name": agent_name,
                    "timestamp": step_ts,
                    "data": {
                        "parts": [{"text": snippet}],
                    },
                })

        # Final event: agent_complete for the primary agent
        events.append({
            "type": "agent_complete",
            "agent_name": primary_agent,
            "timestamp": int(phase_end),
            "data": {},
        })

        current_offset += phase_duration

    # Sort events by timestamp (should already be sorted, but be safe)
    events.sort(key=lambda e: e["timestamp"])

    return events


@app.get("/api/v1/orchestration/{session_id}/events/reconstruct")
async def reconstruct_session_events(session_id: str, user_id: str = "default-user"):
    """Reconstruct synthetic events from session state for completed pipelines.

    This endpoint synthesizes AgentEvent[] from session state keys, enabling
    the Timeline, Chat, and Event Stream tabs to populate for sessions
    loaded from persistent storage (Vertex Session Service) where in-memory
    SSE events are no longer available.
    """
    try:
        session = await app_state.session_service.get_session(
            app_name=SESSION_APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        state = dict(session.state) if session.state else {}
        last_update = getattr(session, "last_update_time", None)

        events = _reconstruct_events_from_state(session_id, state, last_update)

        return {
            "session_id": session_id,
            "events": events,
            "total_events": len(events),
            "reconstructed": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reconstructing events for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reconstruct events: {str(e)}")


@app.get("/api/v1/orchestration/agents", response_model=AgentHierarchyResponse)
async def get_agent_hierarchy():
    """Get agent hierarchy metadata."""
    try:
        # Build agent hierarchy from root_agent
        agents = {}

        def extract_agent_metadata(agent, parent_name=None):
            # Extract tool names safely (tools can be functions or objects)
            tool_names = []
            if hasattr(agent, "tools") and agent.tools:
                for tool in agent.tools:
                    if hasattr(tool, "name"):
                        tool_names.append(tool.name)
                    elif hasattr(tool, "__name__"):
                        tool_names.append(tool.__name__)
                    else:
                        tool_names.append(str(tool))

            metadata = AgentMetadata(
                name=agent.name,
                description=agent.description or "",
                agent_type="root" if parent_name is None else "worker",
                sub_agents=[sa.name for sa in (agent.sub_agents or [])],
                tools=tool_names,
                model=str(agent.model) if hasattr(agent, "model") else "unknown",
            )
            agents[agent.name] = metadata

            # Recursively process sub-agents
            if hasattr(agent, "sub_agents") and agent.sub_agents:
                for sub_agent in agent.sub_agents:
                    extract_agent_metadata(sub_agent, parent_name=agent.name)

        extract_agent_metadata(root_agent)

        return AgentHierarchyResponse(agents=agents, root_agent=root_agent.name)

    except Exception as e:
        logger.error(f"Error getting agent hierarchy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent hierarchy: {str(e)}"
        )


# =====================================
# Trends Endpoints
# =====================================


@app.post("/api/v1/trends/auto-select", response_model=TrendAutoSelectResponse)
async def auto_select_trends(request: TrendAutoSelectRequest):
    """Auto-select trends based on campaign configuration with Gemini safety check + Google Search grounding."""
    try:
        # 1. Fetch available trends (reuse cached if available)
        available = await get_available_trends(force_refresh=False)

        # 2. Run safety check with Google Search grounding on all trends
        all_trends = [
            {"title": t.title, "source": t.source}
            for t in available.search_trends + available.youtube_trends
        ]
        brand = request.campaign_config.get("brand", "")
        audience = request.campaign_config.get("target_audience", "")

        safety_request = TrendSafetyCheckRequest(
            trends=all_trends,
            brand=brand,
            target_audience=audience,
            safety_level="standard",
        )
        safety_response = await check_trend_safety(safety_request)

        # Build lookup of safety results by title
        safety_by_title = {r.trend_title: r for r in safety_response.results}

        # 3. Filter out unsafe trends
        safe_search = [
            t for t in available.search_trends
            if safety_by_title.get(t.title, TrendSafetyResult(
                trend_title=t.title, safe=True, risk_level="safe", reason="", categories=[]
            )).safe
        ]
        safe_yt = [
            t for t in available.youtube_trends
            if safety_by_title.get(t.title, TrendSafetyResult(
                trend_title=t.title, safe=True, risk_level="safe", reason="", categories=[]
            )).safe
        ]

        # 4. Score by keyword relevance to brand/product/audience
        keywords = set()
        for field in ["brand", "target_product", "target_audience", "key_selling_points"]:
            val = request.campaign_config.get(field, "")
            if val:
                keywords.update(w.lower() for w in val.split() if len(w) > 2)

        def relevance_score(trend: TrendInfo) -> float:
            title_lower = trend.title.lower()
            matches = sum(1 for kw in keywords if kw in title_lower)
            return matches / max(len(keywords), 1)

        safe_search.sort(key=relevance_score, reverse=True)
        safe_yt.sort(key=relevance_score, reverse=True)

        # 5. Select requested count
        selected_search = safe_search[: request.num_search_trends]
        selected_yt = safe_yt[: request.num_youtube_trends]

        # 6. Build rationale
        rationale_parts = []
        rationale_parts.append(
            f"Evaluated {len(available.search_trends)} search and {len(available.youtube_trends)} YouTube trends."
        )
        unsafe_count = sum(1 for r in safety_response.results if not r.safe)
        if unsafe_count:
            rationale_parts.append(
                f"Filtered out {unsafe_count} unsafe trend(s) via Gemini + Google Search grounding."
            )
        rationale_parts.append(
            f"Selected {len(selected_search)} search and {len(selected_yt)} YouTube trends"
            + (f" optimized for '{brand}'." if brand else ".")
        )

        return TrendAutoSelectResponse(
            youtube_trends=selected_yt,
            search_trends=selected_search,
            rationale=" ".join(rationale_parts),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-selecting trends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to auto-select trends: {str(e)}"
        )


# In-memory trends cache with 1-hour TTL
_trends_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": 0.0,
}
_TRENDS_CACHE_TTL = 3600  # 1 hour in seconds


@app.get("/api/v1/trends/available", response_model=AvailableTrendsResponse)
async def get_available_trends(force_refresh: bool = Query(default=False)):
    """Get available trends from YouTube Data API and BigQuery Google Trends."""
    try:
        now = time.time()

        # Check cache
        if (
            not force_refresh
            and _trends_cache["data"] is not None
            and (now - _trends_cache["timestamp"]) < _TRENDS_CACHE_TTL
        ):
            logger.info("Returning cached trends (age: %.0fs)", now - _trends_cache["timestamp"])
            return _trends_cache["data"]

        logger.info("Fetching fresh trends from APIs...")

        # Import trend tools
        from .skills.trend_discovery.tools import get_daily_gtrends, get_youtube_trends

        # Fetch Google Search trends from BigQuery
        search_trends = []
        try:
            gtrends_result = get_daily_gtrends()
            if gtrends_result.get("status") == "ok" and gtrends_result.get("markdown_table"):
                # Parse markdown table into TrendInfo objects
                for line in gtrends_result["markdown_table"].split("\n"):
                    line = line.strip()
                    if not line.startswith("|") or "term" in line.lower() or line.startswith("|---") or line.startswith("| ---"):
                        continue
                    # Skip separator lines
                    if all(c in "|- :" for c in line):
                        continue
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cells) >= 3:
                        try:
                            rank = int(cells[0])
                            term = cells[1]
                            refresh_date = str(cells[3]) if len(cells) > 3 else ""
                            search_trends.append(
                                TrendInfo(
                                    trend_id=f"gs-{rank}",
                                    title=term,
                                    source="google_search",
                                    relevance_score=None,
                                    metadata={
                                        "rank": rank,
                                        "refresh_date": refresh_date,
                                    },
                                )
                            )
                        except (ValueError, IndexError):
                            continue
            logger.info("Fetched %d Google Search trends", len(search_trends))
        except Exception as e:
            logger.error("Failed to fetch Google Search trends: %s", e, exc_info=True)

        # Fetch YouTube trends from YouTube Data API
        yt_trends = []
        try:
            yt_result = get_youtube_trends()
            for key, video in yt_result.items():
                if not key.startswith("row_"):
                    continue
                row_num = int(key.split("_")[1])
                yt_trends.append(
                    TrendInfo(
                        trend_id=f"yt-{video.get('videoId', row_num)}",
                        title=video.get("videoTitle", "Untitled"),
                        source="youtube",
                        relevance_score=None,
                        metadata={
                            "rank": row_num,
                            "videoId": video.get("videoId", ""),
                            "videoUrl": video.get("videoURL", ""),
                            "duration": video.get("duration", ""),
                        },
                    )
                )
            logger.info("Fetched %d YouTube trends", len(yt_trends))
        except Exception as e:
            logger.error("Failed to fetch YouTube trends: %s", e, exc_info=True)

        # If both sources returned empty, surface as error
        if not search_trends and not yt_trends:
            raise HTTPException(
                status_code=503,
                detail="Both trend sources returned empty. Check BigQuery and YouTube API access.",
            )

        response = AvailableTrendsResponse(
            youtube_trends=yt_trends,
            search_trends=search_trends,
            last_updated=datetime.utcnow(),
        )

        # Update cache
        _trends_cache["data"] = response
        _trends_cache["timestamp"] = now

        return response

    except Exception as e:
        logger.error(f"Error getting available trends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get available trends: {str(e)}"
        )


# =====================================
# Trend Safety Endpoints
# =====================================


@app.post("/api/v1/trends/safety-check", response_model=TrendSafetyCheckResponse)
async def check_trend_safety(request: TrendSafetyCheckRequest):
    """Evaluate trends for brand safety using Gemini 3 Flash."""
    try:
        from google import genai

        client = genai.Client(vertexai=True)
        today = datetime.utcnow().strftime("%B %d, %Y")

        trend_list = "\n".join(
            f"- {t.get('title', t.get('trend_title', 'Unknown'))}"
            + (f" (Source: {t.get('source', 'unknown')})" if t.get("source") else "")
            + (f" — {t.get('description', '')}" if t.get("description") else "")
            for t in request.trends
        )

        brand_context = f"Brand: {request.brand}" if request.brand else "Brand: not specified"
        audience_context = (
            f"Target audience: {request.target_audience}"
            if request.target_audience
            else ""
        )

        prompt = f"""You are a brand safety analyst. Evaluate each trend below for appropriateness as a marketing campaign topic.

Use Google Search to look up each trend's current context before evaluating brand safety. Consider what the trend actually refers to right now, not just the title.

Today's date: {today}
{brand_context}
{audience_context}
Safety level: {request.safety_level}

TRENDS TO EVALUATE:
{trend_list}

For EACH trend, assess:
1. Is it brand-safe for advertising? (no violence, controversy, adult content, hate speech, political divisiveness, active tragedies/disasters, or culturally insensitive topics)
2. Is it contextually appropriate given today's date? (consider current events, seasonal sensitivity)
3. Would associating a brand with this trend pose reputational risk?

Respond in JSON format (no markdown fencing):
{{
  "results": [
    {{
      "trend_title": "exact trend title",
      "safe": true/false,
      "risk_level": "safe" | "caution" | "unsafe",
      "reason": "brief explanation",
      "categories": ["list of flagged categories if any, e.g. violence, controversy, adult, tragedy, political"]
    }}
  ]
}}

IMPORTANT: Core safety rules that CANNOT be overridden:
- Violence, hate speech, adult/sexual content → always "unsafe"
- Active tragedies, mass casualty events → always "unsafe"
- Extreme political polarization → always "unsafe"
For "standard" safety: flag controversial topics as "caution"
For "strict" safety: flag controversial AND potentially divisive topics as "unsafe"
"""

        from google.genai import types as genai_types

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
            ),
        )

        import json as json_mod

        raw_text = response.text.strip()
        # Strip markdown fencing if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[: raw_text.rfind("```")]

        parsed = json_mod.loads(raw_text)

        results = [
            TrendSafetyResult(
                trend_title=r.get("trend_title", "Unknown"),
                safe=r.get("safe", False),
                risk_level=r.get("risk_level", "caution"),
                reason=r.get("reason", "Unable to assess"),
                categories=r.get("categories", []),
            )
            for r in parsed.get("results", [])
        ]

        return TrendSafetyCheckResponse(
            results=results,
            overall_safe=all(r.safe for r in results),
            checked_at=datetime.utcnow(),
            model_used="gemini-3.0-flash",
        )

    except json_mod.JSONDecodeError as e:
        logger.error("Failed to parse safety check response: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Safety check model returned unparseable response",
        )
    except Exception as e:
        logger.error("Error in trend safety check: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to run safety check: {str(e)}"
        )


# =====================================
# Rating Endpoints
# =====================================


@app.post("/api/v1/rubrics", response_model=RubricResponse)
async def create_rubric(request: RubricCreateRequest):
    """Create or update a rubric."""
    try:
        rubric_id = request.rubric_id or str(uuid.uuid4())
        now = datetime.utcnow()

        # Check if updating existing rubric
        is_update = rubric_id in app_state.rubrics

        rubric = RubricResponse(
            rubric_id=rubric_id,
            name=request.name,
            description=request.description,
            criteria=request.criteria,
            artifact_type=request.artifact_type,
            created_at=app_state.rubrics[rubric_id].created_at if is_update else now,
            updated_at=now,
        )

        app_state.rubrics[rubric_id] = rubric

        return rubric

    except Exception as e:
        logger.error(f"Error creating rubric: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create rubric: {str(e)}")


@app.get("/api/v1/rubrics", response_model=RubricListResponse)
async def list_rubrics():
    """List all rubrics."""
    try:
        return RubricListResponse(rubrics=list(app_state.rubrics.values()))

    except Exception as e:
        logger.error(f"Error listing rubrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list rubrics: {str(e)}")


@app.get("/api/v1/rubrics/{rubric_id}", response_model=RubricResponse)
async def get_rubric(rubric_id: str):
    """Get a specific rubric."""
    try:
        if rubric_id not in app_state.rubrics:
            raise HTTPException(status_code=404, detail=f"Rubric {rubric_id} not found")

        return app_state.rubrics[rubric_id]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rubric: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get rubric: {str(e)}")


@app.post("/api/v1/ratings", response_model=RatingResponse)
async def submit_rating(request: RatingSubmitRequest):
    """Submit a rating for an artifact."""
    try:
        # Get the rubric to calculate weighted score
        if request.rubric_id not in app_state.rubrics:
            raise HTTPException(
                status_code=404, detail=f"Rubric {request.rubric_id} not found"
            )

        rubric = app_state.rubrics[request.rubric_id]

        # Calculate overall weighted score
        total_weight = sum(c.weight for c in rubric.criteria)
        weighted_sum = 0.0

        for rating in request.ratings:
            # Find the criterion
            criterion = next(
                (c for c in rubric.criteria if c.criterion_id == rating.criterion_id),
                None,
            )
            if not criterion:
                raise HTTPException(
                    status_code=400,
                    detail=f"Criterion {rating.criterion_id} not found in rubric",
                )

            # Validate rating is within scale
            if not (criterion.scale_min <= rating.rating <= criterion.scale_max):
                raise HTTPException(
                    status_code=400,
                    detail=f"Rating {rating.rating} for criterion {rating.criterion_id} is outside scale [{criterion.scale_min}, {criterion.scale_max}]",
                )

            # Normalize to 0-1 scale and apply weight
            normalized = (rating.rating - criterion.scale_min) / (
                criterion.scale_max - criterion.scale_min
            )
            weighted_sum += normalized * criterion.weight

        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Create rating response
        rating_id = str(uuid.uuid4())
        rating_response = RatingResponse(
            rating_id=rating_id,
            session_id=request.session_id,
            artifact_key=request.artifact_key,
            rubric_id=request.rubric_id,
            ratings=request.ratings,
            overall_score=overall_score,
            overall_comment=request.overall_comment,
            rater_id=request.rater_id,
            created_at=datetime.utcnow(),
        )

        # Store rating
        app_state.ratings[rating_id] = rating_response

        return rating_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting rating: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")


@app.get("/api/v1/ratings", response_model=RatingListResponse)
async def get_ratings(
    session_id: Optional[str] = Query(default=None),
    artifact_key: Optional[str] = Query(default=None),
    rubric_id: Optional[str] = Query(default=None),
):
    """Get ratings, optionally filtered by session, artifact, or rubric."""
    try:
        # Filter ratings
        filtered_ratings = list(app_state.ratings.values())

        if session_id:
            filtered_ratings = [r for r in filtered_ratings if r.session_id == session_id]

        if artifact_key:
            filtered_ratings = [
                r for r in filtered_ratings if r.artifact_key == artifact_key
            ]

        if rubric_id:
            filtered_ratings = [r for r in filtered_ratings if r.rubric_id == rubric_id]

        # Calculate average score
        average_score = None
        if filtered_ratings:
            average_score = sum(r.overall_score for r in filtered_ratings) / len(
                filtered_ratings
            )

        return RatingListResponse(ratings=filtered_ratings, average_score=average_score)

    except Exception as e:
        logger.error(f"Error getting ratings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get ratings: {str(e)}")


# =====================================
# Narrative Refinement & PDF Generation
# =====================================


@app.post("/api/v1/narrative/refine", response_model=NarrativeRefineResponse)
async def refine_narrative(request: NarrativeRefineRequest):
    """Refine narrative text using a lightweight Gemini call.

    This does NOT go through the full pipeline agent. It uses a direct
    Gemini API call to rewrite the given text based on the user's direction.
    """
    try:
        from google import genai

        # Load report text from session if not provided
        text_to_refine = request.current_text
        brand = ""
        product = ""

        if not text_to_refine and app_state.session_service:
            try:
                session = await app_state.session_service.get_session(
                    app_name=SESSION_APP_NAME,
                    user_id="default-user",
                    session_id=request.session_id,
                )
                if session and session.state:
                    text_to_refine = (
                        session.state.get("final_report_with_citations")
                        or session.state.get("combined_final_cited_report")
                        or ""
                    )
                    brand = session.state.get("brand", "")
                    product = session.state.get("target_product", "")
            except Exception as e:
                logger.warning("Could not load session for narrative: %s", e)

        if not text_to_refine:
            raise HTTPException(
                status_code=400,
                detail="No text to refine. Provide current_text or ensure session has a report.",
            )

        # Truncate to avoid hitting token limits (keep first ~30K chars)
        if len(text_to_refine) > 30000:
            text_to_refine = text_to_refine[:30000] + "\n\n[... truncated for refinement ...]"

        brand_ctx = f"Brand: {brand}, Product: {product}" if brand else ""

        prompt = f"""You are a creative narrative director for advertising campaigns.
{brand_ctx}

The user wants you to refine the following marketing narrative/report.

USER DIRECTION: {request.direction}

CURRENT TEXT:
{text_to_refine}

INSTRUCTIONS:
- Apply the user's direction to rewrite the text
- Maintain the same structure and sections
- Keep factual data, statistics, and citations intact
- Make the changes feel natural, not forced
- Return ONLY the refined text, no preamble or meta-commentary
"""

        client = genai.Client(vertexai=True)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_modalities=["TEXT"],
            ),
        )

        refined = response.text.strip() if response.text else text_to_refine
        return NarrativeRefineResponse(
            refined_text=refined,
            direction_applied=request.direction,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Narrative refinement failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Refinement failed: {str(e)}")


@app.post("/api/v1/narrative/pdf", response_model=NarrativePdfResponse)
async def generate_narrative_pdf(request: NarrativePdfRequest):
    """Generate a PDF from narrative/report content and upload to GCS."""
    try:
        import re
        import tempfile
        from fpdf import FPDF
        from google.cloud import storage as gcs_storage

        # Load content from session if not provided
        content = request.content
        brand = ""
        product = ""
        title = request.title or "Marketing Research Report"

        if not content and app_state.session_service:
            try:
                session = await app_state.session_service.get_session(
                    app_name=SESSION_APP_NAME,
                    user_id="default-user",
                    session_id=request.session_id,
                )
                if session and session.state:
                    content = (
                        session.state.get("final_report_with_citations")
                        or session.state.get("combined_final_cited_report")
                        or ""
                    )
                    brand = session.state.get("brand", "")
                    product = session.state.get("target_product", "")
                    if brand:
                        title = f"{brand} — {product or 'Campaign'} Research Report"
            except Exception as e:
                logger.warning("Could not load session for PDF: %s", e)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="No content for PDF. Provide content or ensure session has a report.",
            )

        # Helper to sanitize text for fpdf2 Helvetica (latin-1 only)
        def _sanitize(text: str) -> str:
            replacements = {
                "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
                "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "-",
                "\u00a0": " ", "\u200b": "", "\u2010": "-", "\u2011": "-",
                "\u2012": "-", "\u2015": "--", "\u00b7": "-",
            }
            for orig, repl in replacements.items():
                text = text.replace(orig, repl)
            return text.encode("latin-1", errors="replace").decode("latin-1")

        # Sanitize entire content upfront
        content = _sanitize(content)

        # Build PDF using fpdf2
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.set_left_margin(15)
        pdf.set_right_margin(15)

        # --- Cover page ---
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 28)
        pdf.ln(60)
        pdf.cell(0, 15, _sanitize(title), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 14)
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        pdf.cell(0, 10, date_str, align="C", new_x="LMARGIN", new_y="NEXT")
        if brand:
            pdf.ln(5)
            pdf.set_font("Helvetica", "I", 12)
            pdf.cell(0, 10, _sanitize(f"Prepared for {brand}"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(
            0, 8,
            _sanitize("Generated by Marketing Intelligence Platform -- Powered by Gemini + Vertex AI"),
            align="C", new_x="LMARGIN", new_y="NEXT",
        )

        # --- Content pages ---
        pdf.add_page()

        # Simple markdown-to-pdf rendering
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()

            if not stripped:
                pdf.ln(4)
                continue

            try:
                # Strip markdown formatting
                clean = re.sub(r"[#*_`\[\]]", "", stripped).strip()
                if not clean:
                    continue

                if stripped.startswith("# "):
                    pdf.ln(6)
                    pdf.set_font("Helvetica", "B", 18)
                    pdf.multi_cell(0, 9, clean)
                    pdf.ln(3)
                elif stripped.startswith("## "):
                    pdf.ln(4)
                    pdf.set_font("Helvetica", "B", 15)
                    pdf.multi_cell(0, 8, clean)
                    pdf.ln(2)
                elif stripped.startswith("### "):
                    pdf.ln(3)
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.multi_cell(0, 7, clean)
                    pdf.ln(2)
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    pdf.set_font("Helvetica", "", 10)
                    bullet_text = re.sub(r"^[-*]\s+", "", stripped).strip()
                    bullet_text = re.sub(r"[*_`\[\]]", "", bullet_text)
                    pdf.multi_cell(0, 6, f"  - {bullet_text}")
                elif re.match(r"^\d+\.\s", stripped):
                    pdf.set_font("Helvetica", "", 10)
                    pdf.multi_cell(0, 6, clean)
                else:
                    pdf.set_font("Helvetica", "", 10)
                    pdf.multi_cell(0, 6, clean)
            except Exception:
                # Skip lines that can't be rendered
                continue

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf.output(tmp.name)
            tmp_path = tmp.name

        # Upload to GCS
        bucket_name = os.environ.get("BUCKET", "zghost-media-center").replace("gs://", "")
        blob_name = f"reports/{request.session_id}/report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

        storage_client = gcs_storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(tmp_path, content_type="application/pdf")

        # Make publicly readable
        try:
            blob.make_public()
        except Exception:
            pass  # Bucket may use uniform access

        # Clean up temp file
        os.unlink(tmp_path)

        gcs_uri = f"gs://{bucket_name}/{blob_name}"
        https_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

        # Update session state with PDF URL if possible
        if app_state.session_service:
            try:
                session = await app_state.session_service.get_session(
                    app_name=SESSION_APP_NAME,
                    user_id="default-user",
                    session_id=request.session_id,
                )
                if session:
                    session.state["final_pdf_url"] = gcs_uri
            except Exception as e:
                logger.warning("Could not update session with PDF URL: %s", e)

        return NarrativePdfResponse(pdf_url=https_url, gcs_uri=gcs_uri)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.get("/api/v1/narrative/pdf/{session_id}/download")
async def download_narrative_pdf(session_id: str):
    """Serve the generated PDF for a session by proxying from GCS."""
    try:
        from google.cloud import storage as gcs_storage
        from fastapi.responses import Response

        # Find the most recent PDF for this session
        bucket_name = os.environ.get("BUCKET", "zghost-media-center").replace("gs://", "")
        prefix = f"reports/{session_id}/"

        storage_client = gcs_storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))

        pdf_blobs = [b for b in blobs if b.name.endswith(".pdf")]
        if not pdf_blobs:
            raise HTTPException(status_code=404, detail="No PDF found for this session")

        # Get the most recent one
        latest = sorted(pdf_blobs, key=lambda b: b.time_created, reverse=True)[0]
        pdf_bytes = latest.download_as_bytes()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="report_{session_id}.pdf"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF download failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF download failed: {str(e)}")


# =====================================
# Health Check
# =====================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(app_state.execution_traces),
        "active_dispatches": len(app_state.active_dispatches),
        "total_ratings": len(app_state.ratings),
        "total_rubrics": len(app_state.rubrics),
    }


# =====================================
# Main Entry Point
# =====================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "trends_and_insights_agent.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
