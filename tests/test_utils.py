"""Unit tests for utility functions and edge cases."""

import pytest
from unittest.mock import Mock, patch
from trends_and_insights_agent.shared_libraries.config import (
    config,
    setup_config,
    audio_config,
)


class TestConfigEdgeCases:
    """Edge case tests for configuration."""

    def test_empty_model_name_validation(self):
        """Test that model names are never empty strings."""
        from trends_and_insights_agent.shared_libraries.config import (
            ResearchConfiguration,
        )

        cfg = ResearchConfiguration()
        assert cfg.critic_model != ""
        assert cfg.worker_model != ""
        assert cfg.image_gen_model != ""
        assert cfg.video_gen_model != ""

    def test_quota_values_are_positive(self):
        """Test that quota and limit values are positive integers."""
        assert config.max_results_yt_trends > 0
        assert config.rate_limit_seconds > 0
        assert config.rpm_quota > 0
        assert isinstance(config.max_results_yt_trends, int)
        assert isinstance(config.rate_limit_seconds, int)
        assert isinstance(config.rpm_quota, int)

    def test_commercial_duration_valid_options(self):
        """Test that commercial_duration is one of the valid options."""
        state = setup_config.empty_session_state["state"]
        assert state["commercial_duration"] in [10, 15, 30]

    def test_autopilot_mode_is_boolean(self):
        """Test that autopilot_mode is a boolean."""
        state = setup_config.empty_session_state["state"]
        assert isinstance(state["autopilot_mode"], bool)

    def test_session_state_keys_are_strings(self):
        """Test that all session state keys are strings."""
        state = setup_config.empty_session_state["state"]
        for key in state.keys():
            assert isinstance(key, str)
            assert len(key) > 0


class TestSchemaEdgeCases:
    """Edge case tests for Pydantic schemas."""

    def test_empty_list_fields(self):
        """Test schemas with empty lists."""
        from trends_and_insights_agent.shared_libraries.schema_types import (
            Insights,
            YT_Trends,
            Search_Trends,
        )

        # All should accept empty lists
        insights = Insights(insights=[])
        yt_trends = YT_Trends(yt_trends=[])
        search_trends = Search_Trends(search_trends=[])

        assert insights.insights == []
        assert yt_trends.yt_trends == []
        assert search_trends.search_trends == []

    def test_long_text_fields(self):
        """Test schemas with very long text values."""
        from trends_and_insights_agent.shared_libraries.schema_types import Insight

        long_text = "A" * 10000  # 10k characters
        insight = Insight(
            insight_title="Test",
            insight_text=long_text,
            insight_urls=["url"],
            key_entities=["entity"],
            key_relationships=["rel"],
            key_audiences="audience",
            key_product_insights="insights",
        )

        assert len(insight.insight_text) == 10000

    def test_many_urls(self):
        """Test schemas with many URLs."""
        from trends_and_insights_agent.shared_libraries.schema_types import Insight

        many_urls = [f"https://example{i}.com" for i in range(100)]
        insight = Insight(
            insight_title="Test",
            insight_text="Text",
            insight_urls=many_urls,
            key_entities=["entity"],
            key_relationships=["rel"],
            key_audiences="audience",
            key_product_insights="insights",
        )

        assert len(insight.insight_urls) == 100

    def test_special_characters_in_text(self):
        """Test schemas with special characters."""
        from trends_and_insights_agent.shared_libraries.schema_types import (
            Search_Trend,
        )

        trend = Search_Trend(
            trend_title="Test with émojis 🚀 and spëcial çhars",
            trend_text="Text with <html> & quotes \"test\" and newlines\n\ntabs\t",
            trend_urls=["url"],
            key_entities=["entity"],
            key_relationships=["rel"],
            key_audiences=["audience"],
            key_product_insights=["insights"],
        )

        assert "émojis" in trend.trend_title
        assert "🚀" in trend.trend_title
        assert "\n" in trend.trend_text

    def test_unicode_text(self):
        """Test schemas with Unicode text."""
        from trends_and_insights_agent.shared_libraries.schema_types import YT_Trend

        trend = YT_Trend(
            video_title="测试视频 テスト الاختبار",
            trend_text="Multi-language: 日本語 中文 العربية",
            trend_urls=["url"],
            key_entities=["entity"],
            key_relationships=["rel"],
            key_audiences=["audience"],
            key_product_insights=["insights"],
        )

        assert "测试视频" in trend.video_title
        assert "日本語" in trend.trend_text


class TestCallbackEdgeCases:
    """Edge case tests for callbacks."""

    def test_callback_with_none_state(self):
        """Test callbacks handle None state gracefully."""
        from trends_and_insights_agent.shared_libraries.callbacks import (
            campaign_callback_function,
        )
        from unittest.mock import Mock

        context = Mock()
        context.agent_name = "test"
        context.state = {}

        # Should not raise
        result = campaign_callback_function(context)

    def test_rate_limit_with_zero_quota(self):
        """Test rate limit callback with edge case quota values."""
        from trends_and_insights_agent.shared_libraries.callbacks import (
            rate_limit_callback,
        )
        from trends_and_insights_agent.shared_libraries.config import (
            ResearchConfiguration,
        )
        from unittest.mock import Mock
        import time

        # Create config with low quota
        custom_config = ResearchConfiguration(rpm_quota=1)

        context = Mock()
        context.state = {"timer_start": time.time() - 100, "request_count": 10}
        request = Mock()

        # Should not raise even with exceeded quota
        with patch(
            "trends_and_insights_agent.shared_libraries.callbacks.config", custom_config
        ):
            rate_limit_callback(context, request)

    def test_callback_with_missing_user_content(self):
        """Test callbacks that expect user_content handle None."""
        from trends_and_insights_agent.shared_libraries.callbacks import (
            before_agent_get_user_file,
        )
        from unittest.mock import Mock
        import asyncio

        context = Mock()
        context.user_content = None

        # Should return None (no file)
        result = asyncio.run(before_agent_get_user_file(context))
        assert result is None


class TestConfigDefaults:
    """Tests for configuration default values and ranges."""

    def test_model_names_contain_gemini(self):
        """Test that most model names reference Gemini models."""
        # Most models should be Gemini-based
        assert "gemini" in config.critic_model.lower()
        assert "gemini" in config.worker_model.lower()
        assert "gemini" in config.video_analysis_model.lower()

    def test_video_gen_model_is_veo(self):
        """Test that video generation uses Veo model."""
        assert "veo" in config.video_gen_model.lower()

    def test_max_results_is_reasonable(self):
        """Test that max_results_yt_trends is in reasonable range."""
        assert 1 <= config.max_results_yt_trends <= 100

    def test_rate_limit_is_reasonable(self):
        """Test that rate limit values are reasonable."""
        assert 1 <= config.rate_limit_seconds <= 3600
        assert 1 <= config.rpm_quota <= 10000


class TestAudioConfigEdgeCases:
    """Edge case tests for AudioConfiguration."""

    def test_all_quick_styles_have_required_keys(self):
        """Test that all quick_styles have voice and music."""
        for style_name, style_data in audio_config.quick_styles.items():
            assert "voice" in style_data, f"{style_name} missing voice"
            assert "music" in style_data, f"{style_name} missing music"

    def test_voice_rate_in_valid_range(self):
        """Test that voice rate values are in reasonable range."""
        for style_name, style_data in audio_config.quick_styles.items():
            rate = style_data["voice"]["rate"]
            assert 0.5 <= rate <= 2.0, f"{style_name} rate out of range: {rate}"

    def test_voice_pitch_in_valid_range(self):
        """Test that voice pitch values are in reasonable range."""
        for style_name, style_data in audio_config.quick_styles.items():
            pitch = style_data["voice"]["pitch"]
            assert -10.0 <= pitch <= 10.0, f"{style_name} pitch out of range: {pitch}"

    def test_music_tempo_format(self):
        """Test that music tempo is properly formatted."""
        for style_name, style_data in audio_config.quick_styles.items():
            tempo = style_data["music"]["tempo"]
            assert isinstance(tempo, str), f"{style_name} tempo should be string"
            assert "BPM" in tempo, f"{style_name} tempo missing BPM"


class TestStateInitialization:
    """Tests for state initialization logic."""

    def test_state_init_key_uniqueness(self):
        """Test that state_init key is unlikely to collide."""
        key = setup_config.state_init
        assert key.startswith("_")  # Internal key convention
        assert len(key) > 3  # Not too short

    def test_empty_state_completeness(self):
        """Test that empty_session_state has all required template variables."""
        state = setup_config.empty_session_state["state"]

        # Template variables used in prompts should exist
        required_vars = [
            "brand",
            "target_product",
            "target_audience",
            "key_selling_points",
            "yt_video_analysis",
            "combined_web_search_insights",
            "combined_final_cited_report",
        ]

        for var in required_vars:
            assert var in state, f"Missing required template variable: {var}"

    def test_nested_dict_structure(self):
        """Test that nested dict fields are properly initialized."""
        state = setup_config.empty_session_state["state"]

        nested_fields = [
            "final_select_ad_copies",
            "final_select_vis_concepts",
            "img_artifact_keys",
            "vid_artifact_keys",
            "target_search_trends",
            "target_yt_trends",
        ]

        for field in nested_fields:
            assert isinstance(
                state[field], dict
            ), f"{field} should be dict, got {type(state[field])}"
            assert (
                field in state[field]
            ), f"{field} should contain key '{field}' (nested structure)"
            assert isinstance(
                state[field][field], list
            ), f"{field}[{field}] should be list"
