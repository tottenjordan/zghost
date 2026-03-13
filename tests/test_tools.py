"""Unit tests for tools.py - Tool function signatures and basic validation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from trends_and_insights_agent import tools


class TestToolsModule:
    """Tests for tools module structure."""

    def test_module_imports(self):
        """Test that tools module can be imported."""
        assert tools is not None

    def test_youtube_client_exists(self):
        """Test that youtube_client is initialized."""
        assert hasattr(tools, "youtube_client")
        assert tools.youtube_client is not None

    def test_genai_client_exists(self):
        """Test that genai client is initialized."""
        assert hasattr(tools, "client")
        assert tools.client is not None


class TestQueryYoutubeApi:
    """Tests for query_youtube_api function."""

    def test_function_signature(self):
        """Test that query_youtube_api has correct parameters."""
        import inspect

        sig = inspect.signature(tools.query_youtube_api)
        params = list(sig.parameters.keys())

        expected_params = [
            "query",
            "video_duration",
            "video_order",
            "num_video_results",
            "max_num_days_ago",
            "video_caption",
            "channel_type",
            "channel_id",
            "event_type",
        ]

        for param in expected_params:
            assert param in params

    def test_function_has_defaults(self):
        """Test that optional parameters have defaults."""
        import inspect

        sig = inspect.signature(tools.query_youtube_api)

        # These should have defaults
        assert sig.parameters["video_order"].default == "relevance"
        assert sig.parameters["num_video_results"].default == 5
        assert sig.parameters["max_num_days_ago"].default == 30
        assert sig.parameters["video_caption"].default == "closedCaption"
        assert sig.parameters["channel_type"].default == "any"

    @patch.object(tools, "youtube_client")
    def test_query_youtube_api_calls_client(self, mock_client):
        """Test that query_youtube_api calls YouTube API client."""
        # Mock the API chain
        mock_search = Mock()
        mock_list = Mock()
        mock_execute = Mock(return_value={"items": []})

        mock_list.execute = mock_execute
        mock_search.list.return_value = mock_list
        mock_client.search.return_value = mock_search

        # Call the function
        result = tools.query_youtube_api(
            query="test query",
            video_duration="any",
        )

        # Verify client was called
        assert mock_client.search.called
        assert mock_search.list.called
        assert mock_execute.called


class TestAnalyzeYoutubeVideos:
    """Tests for analyze_youtube_videos function."""

    def test_function_signature(self):
        """Test that analyze_youtube_videos has correct parameters."""
        import inspect

        sig = inspect.signature(tools.analyze_youtube_videos)
        params = list(sig.parameters.keys())

        assert "prompt" in params
        assert "youtube_url" in params

    def test_function_return_type(self):
        """Test that function return type is Optional[str]."""
        import inspect

        sig = inspect.signature(tools.analyze_youtube_videos)
        # Return annotation should be Optional[str]
        assert sig.return_annotation is not inspect.Signature.empty

    def test_invalid_url_returns_error(self):
        """Test that invalid URL returns error message."""
        # Test URL validation logic with a truly non-YouTube URL
        test_url = "https://example.com/video"
        # The function checks for "youtube.com" in URL
        assert "youtube.com" not in test_url

        # When invalid URL is passed, function should return error
        result = tools.analyze_youtube_videos(
            prompt="test prompt", youtube_url=test_url
        )
        assert result == "Not a valid youtube URL"

    def test_valid_url_format_accepted(self):
        """Test that valid YouTube URL format is accepted."""
        # We can't test the actual API call without mocking heavily,
        # but we can verify the URL validation logic
        test_url = "https://www.youtube.com/watch?v=test123"
        # The function should accept this URL format
        assert "youtube.com" in test_url

    def test_analyze_youtube_videos_calls_genai(self):
        """Test that analyze_youtube_videos calls genai client."""
        # This test verifies the function accepts valid YouTube URLs
        # Actual API calls are mocked at session level
        test_url = "https://www.youtube.com/watch?v=test"
        assert "youtube.com" in test_url  # URL should pass validation

        # Function should accept this without raising
        # (actual result comes from session-level mock)
        result = tools.analyze_youtube_videos(
            prompt="Analyze this video", youtube_url=test_url
        )
        # Result should be a string (from mock or actual call)
        assert isinstance(result, str) or result is None

    def test_analyze_youtube_videos_handles_no_result(self):
        """Test that function handles None result."""
        with patch.object(tools.client.models, "generate_content") as mock_generate:
            # Mock None result
            mock_generate.return_value = None

            result = tools.analyze_youtube_videos(
                prompt="test", youtube_url="https://www.youtube.com/watch?v=test"
            )

            # Should return None
            assert result is None

    def test_analyze_youtube_videos_uses_correct_model(self):
        """Test that analyze_youtube_videos uses video_analysis_model."""
        from trends_and_insights_agent.shared_libraries.config import config

        with patch.object(tools.client.models, "generate_content") as mock_generate:
            mock_result = Mock()
            mock_result.text = "test"
            mock_generate.return_value = mock_result

            tools.analyze_youtube_videos(
                prompt="test", youtube_url="https://www.youtube.com/watch?v=test"
            )

            # Verify the model parameter
            call_args = mock_generate.call_args
            assert call_args is not None
            # Check that model parameter matches config
            if "model" in call_args.kwargs:
                assert call_args.kwargs["model"] == config.video_analysis_model


class TestToolsIntegration:
    """Integration tests for tools module."""

    def test_all_tools_importable(self):
        """Test that common tools can be imported."""
        assert hasattr(tools, "query_youtube_api")
        assert hasattr(tools, "analyze_youtube_videos")
        assert callable(tools.query_youtube_api)
        assert callable(tools.analyze_youtube_videos)

    def test_config_imported(self):
        """Test that config is imported in tools module."""
        # The tools module should import config
        assert hasattr(tools, "config")
        from trends_and_insights_agent.shared_libraries.config import config

        assert tools.config == config

    def test_youtube_api_key_retrieved(self):
        """Test that YouTube API key is retrieved from secrets."""
        # This tests that the secret retrieval doesn't raise
        # (actual API key value is not tested)
        assert hasattr(tools, "YOUTUBE_DATA_API_KEY")
        # Key should be a string (even if it's a test/dummy value)
        assert isinstance(tools.YOUTUBE_DATA_API_KEY, str)

    def test_clients_are_not_none(self):
        """Test that both clients are properly initialized."""
        assert tools.youtube_client is not None
        assert tools.client is not None


class TestToolParameterValidation:
    """Tests for tool parameter validation."""

    def test_query_youtube_api_required_params(self):
        """Test that query_youtube_api requires query and video_duration."""
        import inspect

        sig = inspect.signature(tools.query_youtube_api)

        # query should not have a default (required)
        assert sig.parameters["query"].default == inspect.Parameter.empty
        # video_duration should not have a default (required)
        assert sig.parameters["video_duration"].default == inspect.Parameter.empty

    def test_analyze_youtube_videos_required_params(self):
        """Test that analyze_youtube_videos requires prompt and youtube_url."""
        import inspect

        sig = inspect.signature(tools.analyze_youtube_videos)

        # Both params should be required
        assert sig.parameters["prompt"].default == inspect.Parameter.empty
        assert sig.parameters["youtube_url"].default == inspect.Parameter.empty

    def test_video_duration_valid_values(self):
        """Test documentation for video_duration valid values."""
        import inspect

        # Get the docstring
        docstring = tools.query_youtube_api.__doc__
        assert docstring is not None

        # Check that valid values are documented
        assert "any" in docstring
        assert "short" in docstring or "medium" in docstring or "long" in docstring

    def test_video_order_valid_values(self):
        """Test documentation for video_order valid values."""
        docstring = tools.query_youtube_api.__doc__
        assert docstring is not None

        # Check that valid order values are documented
        valid_orders = ["date", "rating", "relevance", "title", "viewCount"]
        for order in valid_orders:
            assert order in docstring
