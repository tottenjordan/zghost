"""
Pydantic models for the FastAPI backend.
Defines request and response schemas for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# =====================================
# Session Management Models
# =====================================


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""

    preset_config: Optional[str] = Field(
        default=None,
        description="Optional preset configuration name (e.g., 'pixel', 'example_state_pixel')",
    )
    initial_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional initial state to preload into the session",
    )


class SessionCreateResponse(BaseModel):
    """Response when creating a new session."""

    session_id: str = Field(description="Unique session identifier")
    user_id: str = Field(description="User ID associated with the session")
    created_at: datetime = Field(description="Timestamp when session was created")
    agent_engine_id: Optional[str] = Field(
        default=None,
        description="Agent Engine ID if using Vertex AI session service",
    )
    is_vertex_session: bool = Field(
        default=False,
        description="Whether VertexAiSessionService is being used",
    )


class SessionStateResponse(BaseModel):
    """Response containing session state."""

    session_id: str
    state: Dict[str, Any] = Field(description="Full session state dictionary")


class SessionStateUpdateRequest(BaseModel):
    """Request to update specific session state keys."""

    updates: Dict[str, Any] = Field(
        description="Dictionary of state keys to update with their new values"
    )


class SessionSummary(BaseModel):
    """Summary of a session for the sessions list endpoint."""

    session_id: str = Field(description="Unique session identifier")
    user_id: str = Field(description="User ID")
    last_update_time: float = Field(default=0.0, description="Epoch seconds of last update")
    brand: Optional[str] = Field(default=None)
    target_product: Optional[str] = Field(default=None)
    target_audience: Optional[str] = Field(default=None)
    commercial_duration: Optional[int] = Field(default=None)
    autopilot_mode: Optional[bool] = Field(default=None)
    status: Optional[str] = Field(default=None, description="Pipeline phase or completion status")
    has_report: bool = Field(default=False)
    has_commercial: bool = Field(default=False)
    has_images: bool = Field(default=False)
    has_videos: bool = Field(default=False)
    image_count: int = Field(default=0)
    video_count: int = Field(default=0)
    agent_engine_id: Optional[str] = Field(
        default=None,
        description="Agent Engine ID if available (from session state or environment)",
    )


class SessionListResponse(BaseModel):
    """Response listing all sessions."""

    sessions: List[SessionSummary]
    total: int


class ArtifactInfo(BaseModel):
    """Information about a session artifact."""

    key: str = Field(description="Artifact key/name")
    version: int = Field(description="Artifact version number")
    mime_type: Optional[str] = Field(default=None, description="MIME type of artifact")
    size_bytes: Optional[int] = Field(default=None, description="Size in bytes")
    created_at: Optional[datetime] = Field(
        default=None, description="When artifact was created"
    )


class SessionArtifactsResponse(BaseModel):
    """Response listing session artifacts."""

    session_id: str
    artifacts: List[ArtifactInfo]


# =====================================
# Agent Execution Models
# =====================================


class AgentRunRequest(BaseModel):
    """Request to run agent with a message."""

    session_id: Optional[str] = Field(
        default=None, description="Session ID (created if not provided)"
    )
    user_id: Optional[str] = Field(
        default=None, description="User ID (defaults to 'default-user')"
    )
    message: str = Field(description="User message to send to the agent")


class AgentRunResponse(BaseModel):
    """Response from agent execution."""

    session_id: str
    user_id: str
    stream_url: str = Field(
        description="URL to connect to for SSE streaming of agent events"
    )


# =====================================
# Parallel Dispatch Models
# =====================================


class StreamConfig(BaseModel):
    """Configuration for a single parallel stream."""

    name: str = Field(description="Unique name for this stream")
    trend_config: Dict[str, Any] = Field(
        description="Trend configuration to apply (e.g., target_yt_trends, target_search_trends)"
    )
    session_preset: Optional[str] = Field(
        default=None, description="Optional session preset to use"
    )
    initial_message: Optional[str] = Field(
        default=None,
        description="Optional initial message to send after configuration",
    )


class DispatchConfig(BaseModel):
    """Configuration for parallel dispatch."""

    streams: List[StreamConfig] = Field(
        description="List of stream configurations to run in parallel"
    )
    max_parallel: Optional[int] = Field(
        default=None,
        description="Maximum number of parallel streams (defaults to len(streams))",
    )


class StreamInfo(BaseModel):
    """Information about a dispatched stream."""

    stream_id: str = Field(description="Unique identifier for this stream")
    stream_name: str = Field(description="Human-readable name for the stream")
    session_id: str = Field(description="ADK session ID for this stream")
    status: str = Field(
        description="Stream status: 'pending', 'running', 'completed', 'failed', 'cancelled'"
    )
    created_at: datetime


class DispatchResponse(BaseModel):
    """Response from creating a parallel dispatch."""

    dispatch_id: str = Field(description="Unique identifier for this dispatch batch")
    streams: List[StreamInfo] = Field(description="Information about each stream")
    stream_url: str = Field(
        description="Multiplexed SSE stream URL for all parallel streams"
    )


class StreamEvent(BaseModel):
    """A multiplexed event from a parallel stream."""

    stream_id: str = Field(description="Which stream this event came from")
    stream_name: str = Field(description="Human-readable stream name")
    event_type: str = Field(
        description="Event type: 'agent_start', 'agent_end', 'model_response', 'tool_call', 'error'"
    )
    data: Dict[str, Any] = Field(description="Event payload")
    timestamp: datetime


# =====================================
# Orchestration Models
# =====================================


class AgentStatus(BaseModel):
    """Status of a single agent in the hierarchy."""

    agent_name: str
    status: str = Field(
        description="Agent status: 'idle', 'running', 'waiting', 'completed', 'failed'"
    )
    current_tool: Optional[str] = Field(
        default=None, description="Currently executing tool, if any"
    )
    parent_agent: Optional[str] = Field(
        default=None, description="Name of parent agent"
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PipelineStatus(BaseModel):
    """Status of an active pipeline."""

    session_id: str
    pipeline_name: str = Field(
        description="Name of the pipeline (e.g., 'research_pipeline', 'ad_creative_pipeline')"
    )
    status: str = Field(description="Pipeline status: 'running', 'completed', 'failed'")
    agents: List[AgentStatus] = Field(
        description="Status of agents involved in this pipeline"
    )
    started_at: datetime
    completed_at: Optional[datetime] = None


class OrchestrationStatusResponse(BaseModel):
    """Response containing all active pipeline statuses."""

    active_pipelines: List[PipelineStatus]
    total_sessions: int = Field(description="Total number of active sessions")


class TraceEvent(BaseModel):
    """A single event in the execution trace."""

    event_id: str
    timestamp: datetime
    agent_name: str
    event_type: str = Field(
        description="Type: 'agent_invoked', 'tool_called', 'model_called', 'agent_completed'"
    )
    details: Dict[str, Any] = Field(description="Event-specific details")
    parent_event_id: Optional[str] = Field(
        default=None, description="ID of parent event in trace"
    )


class ExecutionTraceResponse(BaseModel):
    """Response containing execution trace for a session."""

    session_id: str
    events: List[TraceEvent] = Field(description="Chronological list of trace events")
    total_events: int


class AgentMetadata(BaseModel):
    """Metadata about an agent in the hierarchy."""

    name: str
    description: str
    agent_type: str = Field(
        description="Type: 'root', 'orchestrator', 'pipeline', 'worker'"
    )
    sub_agents: List[str] = Field(
        default_factory=list, description="Names of sub-agents"
    )
    tools: List[str] = Field(default_factory=list, description="Available tool names")
    model: str = Field(description="LLM model used by this agent")


class AgentHierarchyResponse(BaseModel):
    """Response containing agent hierarchy metadata."""

    agents: Dict[str, AgentMetadata] = Field(
        description="Map of agent name to metadata"
    )
    root_agent: str = Field(description="Name of the root agent")


# =====================================
# Trends Models
# =====================================


class TrendAutoSelectRequest(BaseModel):
    """Request to auto-select trends based on campaign config."""

    campaign_config: Dict[str, Any] = Field(
        description="Campaign configuration (brand, target_product, target_audience, etc.)"
    )
    num_youtube_trends: int = Field(
        default=3, description="Number of YouTube trends to select"
    )
    num_search_trends: int = Field(
        default=3, description="Number of Google Search trends to select"
    )


class TrendInfo(BaseModel):
    """Information about a trend."""

    trend_id: str
    title: str
    source: str = Field(description="Source: 'youtube' or 'google_search'")
    relevance_score: Optional[float] = Field(
        default=None, description="Relevance score 0-1"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional trend metadata"
    )


class TrendAutoSelectResponse(BaseModel):
    """Response from auto-selecting trends."""

    youtube_trends: List[TrendInfo]
    search_trends: List[TrendInfo]
    rationale: str = Field(
        description="Explanation of why these trends were selected"
    )


class AvailableTrendsResponse(BaseModel):
    """Response containing available trends from APIs."""

    youtube_trends: List[TrendInfo]
    search_trends: List[TrendInfo]
    last_updated: datetime


# =====================================
# Trend Safety Models
# =====================================


class TrendSafetyCheckRequest(BaseModel):
    """Request to validate trends for brand safety."""

    trends: List[Dict[str, Any]] = Field(
        description="List of trend objects to evaluate"
    )
    brand: str = Field(default="", description="Brand name for context")
    target_audience: str = Field(
        default="", description="Target audience for context"
    )
    safety_level: str = Field(
        default="standard",
        description="Safety strictness: 'standard' or 'strict'",
    )


class TrendSafetyResult(BaseModel):
    """Safety evaluation result for a single trend."""

    trend_title: str
    safe: bool = Field(description="Whether the trend passes safety checks")
    risk_level: str = Field(
        description="Risk level: 'safe', 'caution', 'unsafe'"
    )
    reason: str = Field(description="Explanation of the safety assessment")
    categories: List[str] = Field(
        default_factory=list,
        description="Flagged categories: e.g. 'violence', 'controversy', 'adult'",
    )


class TrendSafetyCheckResponse(BaseModel):
    """Response from trend safety check."""

    results: List[TrendSafetyResult]
    overall_safe: bool = Field(
        description="True if all trends passed safety checks"
    )
    checked_at: datetime
    model_used: str = Field(default="gemini-3.0-flash")


# =====================================
# Rating Models
# =====================================


class RubricCriterion(BaseModel):
    """A single criterion in a rating rubric."""

    criterion_id: str
    name: str
    description: str
    scale_min: int = Field(default=1, description="Minimum rating value")
    scale_max: int = Field(default=5, description="Maximum rating value")
    weight: float = Field(default=1.0, description="Weight of this criterion")


class RubricCreateRequest(BaseModel):
    """Request to create or update a rubric."""

    rubric_id: Optional[str] = Field(
        default=None, description="Rubric ID (generated if not provided)"
    )
    name: str = Field(description="Rubric name")
    description: str = Field(description="Description of what this rubric evaluates")
    criteria: List[RubricCriterion] = Field(description="List of rating criteria")
    artifact_type: str = Field(
        description="Type of artifact this rubric evaluates (e.g., 'ad_copy', 'visual_concept', 'research_report')"
    )


class RubricResponse(BaseModel):
    """Response containing a rubric."""

    rubric_id: str
    name: str
    description: str
    criteria: List[RubricCriterion]
    artifact_type: str
    created_at: datetime
    updated_at: datetime


class RubricListResponse(BaseModel):
    """Response listing all rubrics."""

    rubrics: List[RubricResponse]


class CriterionRating(BaseModel):
    """A rating for a single criterion."""

    criterion_id: str
    rating: int = Field(description="Rating value within the criterion's scale")
    comment: Optional[str] = Field(
        default=None, description="Optional comment for this criterion"
    )


class RatingSubmitRequest(BaseModel):
    """Request to submit a rating."""

    session_id: str = Field(
        description="Session ID that produced the artifact being rated"
    )
    artifact_key: str = Field(description="Key of the artifact being rated")
    rubric_id: str = Field(description="ID of the rubric being used")
    ratings: List[CriterionRating] = Field(description="Ratings for each criterion")
    overall_comment: Optional[str] = Field(
        default=None, description="Overall comment on the artifact"
    )
    rater_id: Optional[str] = Field(
        default=None, description="ID of the person providing the rating"
    )


class RatingResponse(BaseModel):
    """Response containing a submitted rating."""

    rating_id: str
    session_id: str
    artifact_key: str
    rubric_id: str
    ratings: List[CriterionRating]
    overall_score: float = Field(
        description="Weighted average score across all criteria"
    )
    overall_comment: Optional[str] = None
    rater_id: Optional[str] = None
    created_at: datetime


class RatingListResponse(BaseModel):
    """Response listing ratings."""

    ratings: List[RatingResponse]
    average_score: Optional[float] = Field(
        default=None, description="Average overall score across all ratings"
    )


# =====================================
# Narrative Models
# =====================================


class NarrativeRefineRequest(BaseModel):
    """Request to refine a narrative using Gemini."""

    session_id: str = Field(description="Session ID to load context from")
    direction: str = Field(description="User's refinement direction, e.g. 'add humor'")
    current_text: Optional[str] = Field(
        default=None, description="Optional: override text to refine (otherwise loads from session)"
    )


class NarrativeRefineResponse(BaseModel):
    """Response with refined narrative text."""

    refined_text: str = Field(description="The refined narrative text")
    direction_applied: str = Field(description="The direction that was applied")


class NarrativePdfRequest(BaseModel):
    """Request to generate a PDF from narrative content."""

    session_id: str = Field(description="Session ID for context")
    content: Optional[str] = Field(
        default=None, description="Optional: text content to render as PDF (otherwise loads report from session)"
    )
    title: Optional[str] = Field(
        default="Marketing Research Report", description="PDF title"
    )


class NarrativePdfResponse(BaseModel):
    """Response with the generated PDF URL."""

    pdf_url: str = Field(description="Public HTTPS URL to the generated PDF")
    gcs_uri: str = Field(description="GCS URI of the uploaded PDF")


# =====================================
# Concurrency Control Models
# =====================================


class ConcurrencyStatusResponse(BaseModel):
    """Response containing current concurrency status."""

    active_count: int = Field(description="Number of currently running pipelines")
    max_concurrent: int = Field(description="Maximum allowed concurrent pipelines")
    queued_count: int = Field(default=0, description="Number of pipelines waiting in queue")


class ConcurrencyConfigRequest(BaseModel):
    """Request to update concurrency configuration."""

    max_concurrent: int = Field(
        description="New maximum concurrent pipelines", ge=1, le=20
    )


# =====================================
# Evaluation Models
# =====================================


class EvalCriterion(BaseModel):
    """A criterion for AI evaluation (mirrors frontend rubric)."""

    name: str = Field(description="Criterion name")
    description: str = Field(description="What this criterion evaluates")
    weight: float = Field(default=1.0, description="Weight of this criterion")


class EvalRunRequest(BaseModel):
    """Request to run an evaluation."""

    eval_set_path: str = Field(description="Path to eval dataset JSON file")
    agent_module: str = Field(
        default="trends_and_insights_agent",
        description="Python module path to agent",
    )
    rubric_criteria: Optional[List[EvalCriterion]] = Field(
        default=None,
        description="Optional custom rubric criteria for AI evaluation",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID to pull pipeline outputs from for evaluation",
    )
    brand: Optional[str] = Field(
        default=None,
        description="Brand name for evaluation context",
    )
    target_product: Optional[str] = Field(
        default=None,
        description="Target product for evaluation context",
    )


class EvalRunResponse(BaseModel):
    """Response from starting an evaluation."""

    eval_id: str = Field(description="Unique identifier for this evaluation run")
    status: str = Field(description="Status: 'pending', 'running', 'completed', 'failed'")
    results: Optional[Dict[str, Any]] = Field(
        default=None, description="Evaluation results (available when completed)"
    )
    started_at: datetime = Field(description="When evaluation was started")
    completed_at: Optional[datetime] = Field(
        default=None, description="When evaluation completed"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session ID used for evaluation context"
    )
    brand: Optional[str] = Field(
        default=None, description="Brand evaluated"
    )
    target_product: Optional[str] = Field(
        default=None, description="Target product evaluated"
    )


class EvalSetInfo(BaseModel):
    """Information about an evaluation dataset."""

    name: str = Field(description="Eval set name (filename without .test.json)")
    path: str = Field(description="Full path to eval set file")
    num_cases: int = Field(description="Number of test cases in this eval set")


class EvalSetListResponse(BaseModel):
    """Response listing available evaluation datasets."""

    eval_sets: List[EvalSetInfo]
