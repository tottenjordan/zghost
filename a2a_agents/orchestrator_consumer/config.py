"""Configuration for orchestrator consumer agent."""

from dataclasses import dataclass


@dataclass
class ResearchConfiguration:
    """Configuration for research-related models and parameters."""
    
    critic_model: str = "gemini-2.5-pro"
    worker_model: str = "gemini-2.5-flash"
    video_analysis_model: str = "gemini-2.5-pro"
    lite_planner_model: str = "gemini-2.0-flash-001"
    image_gen_model: str = "imagen-4.0-fast-generate-preview-06-06"
    video_gen_model: str = "veo-3.0-generate-preview"
    max_results_yt_trends: int = 45
    rate_limit_seconds: int = 60
    rpm_quota: int = 1000


config = ResearchConfiguration()