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
from .api_models import (
    AgentHierarchyResponse,
    AgentMetadata,
    AgentRunRequest,
    AgentRunResponse,
    ArtifactInfo,
    AvailableTrendsResponse,
    DispatchConfig,
    DispatchResponse,
    ExecutionTraceResponse,
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

        # Create session with state included (InMemorySessionService returns
        # a deep copy, so we must pass state at creation time)
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

        return SessionCreateResponse(
            session_id=session_id, user_id=user_id, created_at=datetime.utcnow()
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


@app.get("/api/v1/run/{session_id}/stream")
async def stream_agent_run(
    session_id: str, user_id: str = Query(default="default-user"), message: str = Query(...)
):
    """SSE stream for agent execution."""
    return StreamingResponse(
        stream_agent_events(app_state.runner, session_id, user_id, message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
    """Auto-select trends based on campaign configuration."""
    try:
        # This would integrate with the trends_and_insights_agent
        # For now, return a placeholder response
        # TODO: Implement actual trend selection logic

        return TrendAutoSelectResponse(
            youtube_trends=[],
            search_trends=[],
            rationale="Auto-selection not yet implemented. Please use the agent's interactive trend selection.",
        )

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

        response = client.models.generate_content(
            model="gemini-3.0-flash",
            contents=prompt,
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
