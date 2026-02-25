"""
Generation configuration management for all agents in the system.
Provides optimized temperature and generation parameters by agent type.
"""

from typing import Optional, Dict, Any
from google.genai import types


class GenerationConfigManager:
    """Manages generation configurations for different agent types."""

    # Default configurations by agent role
    CONFIGS = {
        # Deterministic routing and orchestration
        "orchestrator": {
            "temperature": 0.01,
            "top_p": 0.9,
            "top_k": 20,
            "max_output_tokens": 1000,
            "response_modalities": ["TEXT"],
        },

        # Factual research and analysis
        "researcher": {
            "temperature": 0.5,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 3000,
            "response_modalities": ["TEXT"],
        },

        # Highly factual web search
        "web_searcher": {
            "temperature": 0.3,
            "top_p": 0.85,
            "top_k": 30,
            "max_output_tokens": 2000,
            "response_modalities": ["TEXT"],
        },

        # Balanced trend analysis
        "trend_analyzer": {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 50,
            "max_output_tokens": 2000,
            "response_modalities": ["TEXT"],
        },

        # Maximum creativity for content generation
        "creative_generator": {
            "temperature": 1.5,
            "top_p": 0.95,
            "top_k": 100,
            "max_output_tokens": 1500,
            "response_modalities": ["TEXT"],
        },

        # Balanced evaluation and critique
        "critic": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2000,
            "response_modalities": ["TEXT"],
        },

        # Refinement and finalization
        "finalizer": {
            "temperature": 0.8,
            "top_p": 0.92,
            "top_k": 50,
            "max_output_tokens": 1500,
            "response_modalities": ["TEXT"],
        },

        # Prompt generation for image/video
        "prompt_generator": {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 80,
            "max_output_tokens": 500,
            "response_modalities": ["TEXT"],
        },

        # Video analysis and planning
        "video_analyzer": {
            "temperature": 0.6,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2000,
            "response_modalities": ["TEXT"],
        },
    }

    # Agent name to configuration type mapping
    AGENT_MAPPING = {
        # Root orchestrator
        "root_agent": "orchestrator",

        # Trend discovery skill
        "trends_and_insights_agent": "trend_analyzer",

        # Market research skill
        "research_orchestrator": "researcher",
        "yt_analysis_generator_agent": "video_analyzer",
        "yt_web_planner": "web_searcher",
        "yt_web_searcher": "web_searcher",
        "gs_web_planner": "web_searcher",
        "gs_web_searcher": "web_searcher",
        "campaign_web_planner": "web_searcher",
        "campaign_web_searcher": "web_searcher",
        "merge_planners": "researcher",
        "combined_web_evaluator": "critic",
        "enhanced_combined_searcher": "researcher",
        "combined_report_composer": "finalizer",

        # Ad creative skill
        "ad_content_generator_agent": "orchestrator",
        "ad_copy_drafter": "creative_generator",
        "ad_copy_critic": "critic",
        "visual_concept_drafter": "creative_generator",
        "visual_concept_critic": "critic",
        "visual_concept_finalizer": "finalizer",
        "visual_generator": "prompt_generator",

        # AV studio skill
        "av_editing_studio_agent": "video_analyzer",
    }

    @classmethod
    def get_config(
        cls,
        agent_name: str,
        overrides: Optional[Dict[str, Any]] = None
    ) -> types.GenerateContentConfig:
        """
        Get generation configuration for a specific agent.

        Args:
            agent_name: Name of the agent
            overrides: Optional parameter overrides

        Returns:
            GenerateContentConfig with optimized settings
        """
        # Get the configuration type for this agent
        config_type = cls.AGENT_MAPPING.get(agent_name, "researcher")

        # Get base configuration
        config = cls.CONFIGS[config_type].copy()

        # Apply any overrides
        if overrides:
            config.update(overrides)

        # Create and return the configuration
        return types.GenerateContentConfig(**config)

    @classmethod
    def get_experimental_config(
        cls,
        agent_name: str,
        variation: str = "baseline"
    ) -> types.GenerateContentConfig:
        """
        Get experimental configuration for A/B testing.

        Args:
            agent_name: Name of the agent
            variation: One of "baseline", "lower", "higher"

        Returns:
            GenerateContentConfig for testing
        """
        base_config = cls.get_config(agent_name)
        base_dict = base_config.__dict__.copy()

        if variation == "lower":
            base_dict["temperature"] = max(0.0, base_dict.get("temperature", 0.7) - 0.2)
        elif variation == "higher":
            base_dict["temperature"] = min(2.0, base_dict.get("temperature", 0.7) + 0.2)

        return types.GenerateContentConfig(**base_dict)

    @classmethod
    def validate_temperature(cls, temperature: float, agent_type: str) -> bool:
        """
        Validate if a temperature is appropriate for an agent type.

        Args:
            temperature: Temperature value to validate
            agent_type: Type of agent (from CONFIGS keys)

        Returns:
            True if temperature is within recommended range
        """
        ranges = {
            "orchestrator": (0.0, 0.1),
            "researcher": (0.3, 0.7),
            "web_searcher": (0.2, 0.5),
            "trend_analyzer": (0.5, 0.9),
            "creative_generator": (1.0, 1.8),
            "critic": (0.5, 0.9),
            "finalizer": (0.6, 1.0),
            "prompt_generator": (0.8, 1.3),
            "video_analyzer": (0.4, 0.8),
        }

        min_temp, max_temp = ranges.get(agent_type, (0.0, 2.0))
        return min_temp <= temperature <= max_temp


# Convenience function for backward compatibility
def get_generation_config(
    agent_name: str,
    **overrides
) -> types.GenerateContentConfig:
    """
    Get optimized generation configuration for an agent.

    Args:
        agent_name: Name of the agent
        **overrides: Any parameter overrides

    Returns:
        GenerateContentConfig with optimized settings
    """
    return GenerationConfigManager.get_config(agent_name, overrides)


# Example usage patterns
if __name__ == "__main__":
    # Get standard config for research orchestrator
    research_config = get_generation_config("research_orchestrator")
    print(f"Research config: temp={research_config.temperature}")

    # Get config with override
    custom_config = get_generation_config(
        "ad_copy_drafter",
        temperature=1.3,  # Slightly less creative than default
        max_output_tokens=2000
    )
    print(f"Custom creative config: temp={custom_config.temperature}")

    # Validate temperature
    is_valid = GenerationConfigManager.validate_temperature(
        1.5, "creative_generator"
    )
    print(f"Temperature 1.5 valid for creative: {is_valid}")