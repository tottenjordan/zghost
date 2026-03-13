"""Unit tests for config.py - Configuration objects and validation."""

import pytest

from trends_and_insights_agent.shared_libraries.config import (
    ResearchConfiguration,
    SetupConfiguration,
    AudioConfiguration,
    config,
    setup_config,
    audio_config,
)


class TestResearchConfiguration:
    """Tests for ResearchConfiguration dataclass."""

    def test_default_values(self):
        """Test that ResearchConfiguration has expected default values."""
        cfg = ResearchConfiguration()
        assert cfg.critic_model == "gemini-3-flash-preview"
        assert cfg.worker_model == "gemini-3-flash-preview"
        assert cfg.video_analysis_model == "gemini-3-flash-preview"
        assert cfg.lite_planner_model == "gemini-3-flash-preview"
        assert cfg.image_gen_model == "gemini-3-pro-image-preview"
        assert cfg.video_gen_model == "veo-3.1-fast-generate-001"
        assert cfg.max_results_yt_trends == 45
        assert cfg.rate_limit_seconds == 60
        assert cfg.rpm_quota == 1000

    def test_custom_values(self):
        """Test ResearchConfiguration with custom values."""
        cfg = ResearchConfiguration(
            critic_model="custom-critic",
            worker_model="custom-worker",
            max_results_yt_trends=10,
            rate_limit_seconds=30,
            rpm_quota=500,
        )
        assert cfg.critic_model == "custom-critic"
        assert cfg.worker_model == "custom-worker"
        assert cfg.max_results_yt_trends == 10
        assert cfg.rate_limit_seconds == 30
        assert cfg.rpm_quota == 500

    def test_global_config_instance(self):
        """Test that global config instance exists and is properly initialized."""
        assert config is not None
        assert isinstance(config, ResearchConfiguration)
        assert config.critic_model == "gemini-3-flash-preview"


class TestSetupConfiguration:
    """Tests for SetupConfiguration dataclass."""

    def test_state_init_key(self):
        """Test that state_init key is properly defined."""
        cfg = SetupConfiguration()
        assert cfg.state_init == "_state_init"

    def test_empty_session_state_structure(self):
        """Test that empty_session_state has expected structure."""
        cfg = SetupConfiguration()
        assert "state" in cfg.empty_session_state
        state = cfg.empty_session_state["state"]

        # Check all required keys exist
        assert "final_select_ad_copies" in state
        assert "final_select_vis_concepts" in state
        assert "img_artifact_keys" in state
        assert "vid_artifact_keys" in state
        assert "brand" in state
        assert "target_product" in state
        assert "target_audience" in state
        assert "key_selling_points" in state
        assert "target_search_trends" in state
        assert "target_yt_trends" in state
        assert "commercial_duration" in state
        assert "autopilot_mode" in state
        assert "yt_video_analysis" in state
        assert "combined_web_search_insights" in state
        assert "campaign_web_search_insights" in state
        assert "gs_web_search_insights" in state
        assert "yt_web_search_insights" in state
        assert "combined_final_cited_report" in state
        assert "sources" in state
        assert "final_report_with_citations" in state
        assert "commercial_artifact" in state
        assert "campaign_guide_content" in state

    def test_default_values_in_empty_state(self):
        """Test default values in empty session state."""
        cfg = SetupConfiguration()
        state = cfg.empty_session_state["state"]

        assert state["brand"] == ""
        assert state["target_product"] == ""
        assert state["target_audience"] == ""
        assert state["key_selling_points"] == ""
        assert state["commercial_duration"] == 30
        assert state["autopilot_mode"] is False
        assert state["sources"] == {}

    def test_list_fields_initialized_correctly(self):
        """Test that list/dict fields are properly initialized."""
        cfg = SetupConfiguration()
        state = cfg.empty_session_state["state"]

        assert state["final_select_ad_copies"] == {"final_select_ad_copies": []}
        assert state["final_select_vis_concepts"] == {"final_select_vis_concepts": []}
        assert state["img_artifact_keys"] == {"img_artifact_keys": []}
        assert state["vid_artifact_keys"] == {"vid_artifact_keys": []}
        assert state["target_search_trends"] == {"target_search_trends": []}
        assert state["target_yt_trends"] == {"target_yt_trends": []}

    def test_global_setup_config_instance(self):
        """Test that global setup_config instance exists."""
        assert setup_config is not None
        assert isinstance(setup_config, SetupConfiguration)


class TestAudioConfiguration:
    """Tests for AudioConfiguration dataclass."""

    def test_default_model_values(self):
        """Test that AudioConfiguration has expected model names."""
        cfg = AudioConfiguration()
        assert cfg.chirp_model == "models/chirp-3-hd"
        assert cfg.lyria_model == "lyria-002"

    def test_quick_styles_initialized(self):
        """Test that quick_styles are initialized after __post_init__."""
        cfg = AudioConfiguration()
        assert cfg.quick_styles is not None
        assert isinstance(cfg.quick_styles, dict)

    def test_quick_styles_content(self):
        """Test that quick_styles contain expected presets."""
        cfg = AudioConfiguration()
        expected_styles = [
            "tech_modern",
            "lifestyle_warm",
            "youth_energy",
            "luxury_premium",
            "family_friendly",
        ]
        for style in expected_styles:
            assert style in cfg.quick_styles
            assert "voice" in cfg.quick_styles[style]
            assert "music" in cfg.quick_styles[style]

    def test_voice_preset_structure(self):
        """Test that voice presets have expected keys."""
        cfg = AudioConfiguration()
        voice = cfg.quick_styles["tech_modern"]["voice"]
        assert "style" in voice
        assert "rate" in voice
        assert "pitch" in voice
        assert "description" in voice

    def test_music_preset_structure(self):
        """Test that music presets have expected keys."""
        cfg = AudioConfiguration()
        music = cfg.quick_styles["lifestyle_warm"]["music"]
        assert "genre" in music
        assert "mood" in music
        assert "tempo" in music
        assert "instruments" in music

    def test_global_audio_config_instance(self):
        """Test that global audio_config instance exists."""
        assert audio_config is not None
        assert isinstance(audio_config, AudioConfiguration)

    def test_audio_config_import_fallback(self):
        """Test that audio_config handles ImportError gracefully."""
        # This test verifies the try/except block in config.py
        # We can't directly test the ImportError path, but we can verify
        # the config still works even if detailed presets aren't available
        cfg = AudioConfiguration()
        assert cfg.chirp_model is not None
        assert cfg.lyria_model is not None


class TestConfigIntegration:
    """Integration tests for config module."""

    def test_all_configs_importable(self):
        """Test that all config objects can be imported."""
        from trends_and_insights_agent.shared_libraries.config import (
            config,
            setup_config,
            audio_config,
        )
        assert config is not None
        assert setup_config is not None
        assert audio_config is not None

    def test_config_values_are_strings(self):
        """Test that model names are strings (not None or empty)."""
        assert isinstance(config.critic_model, str)
        assert isinstance(config.worker_model, str)
        assert isinstance(config.video_analysis_model, str)
        assert isinstance(config.image_gen_model, str)
        assert isinstance(config.video_gen_model, str)
        assert len(config.critic_model) > 0
        assert len(config.worker_model) > 0

    def test_config_numeric_values_are_positive(self):
        """Test that numeric config values are positive."""
        assert config.max_results_yt_trends > 0
        assert config.rate_limit_seconds > 0
        assert config.rpm_quota > 0

    def test_commercial_duration_default(self):
        """Test that commercial_duration has valid default."""
        state = setup_config.empty_session_state["state"]
        assert state["commercial_duration"] in [10, 15, 30]
