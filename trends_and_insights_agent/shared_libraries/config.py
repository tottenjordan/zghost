from dataclasses import dataclass


@dataclass
class ResearchConfiguration:
    """Configuration for research-related models and parameters.

    Attributes:
        critic_model (str): Model for evaluation tasks.
        worker_model (str): Model for working/generation tasks.
        video_analysis_model (str): Model for video understanding.
        image_gen_model (str): Model for generating images.
        video_gen_model (str): Model for generating video.
        max_results_yt_trends (int): The value to set for `max_results` with the YouTube API 
                                i.e., the number of video results to return.
        rate_limit_seconds (int): total duration to calculate the rate at which the agent queries the LLM API.
        rpm_quota (int): requests per minute threshold for agent LLM API rate limiter

    """

    critic_model: str = "gemini-2.5-pro"  # "gemini-2.5-pro" | "gemini-2.5-flash"
    worker_model: str = "gemini-2.5-flash"  # "gemini-2.5-flash" | "gemini-2.0-flash"
    video_analysis_model: str = "gemini-2.5-pro"
    lite_planner_model: str = "gemini-2.0-flash-001"

    # "imagen-4.0-ultra-generate-preview-06-06" "imagen-4.0-generate-preview-06-06"
    image_gen_model: str = "imagen-4.0-fast-generate-preview-06-06"

    # "veo-2.0-generate-001" | veo-3.0-generate-preview
    video_gen_model: str = "veo-3.0-generate-preview"

    max_results_yt_trends: int = 45
    rate_limit_seconds: int = 60
    rpm_quota: int = 1000


config = ResearchConfiguration()


@dataclass
class SetupConfiguration:
    """Configuration for general setup

    Attributes:
        state_init (str): a key indicating the state dict is initialized
        empty_session_state (dict): Empty dictionary with keys for initial ADK session state.

    """

    state_init = "_state_init"
    empty_session_state = {
        "state": {
            "img_artifact_keys": {"img_artifact_keys": []},
            "vid_artifact_keys": {"vid_artifact_keys": []},
            "brand": "",
            "target_product": "",
            "target_audience": "",
            "key_selling_points": "",
            "target_search_trends": {"target_search_trends": []},
            "target_yt_trends": {"target_yt_trends": []},
        }
    }


setup_config = SetupConfiguration()
