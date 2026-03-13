"""Unit tests for callbacks.py - Callback function signatures and behavior."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools import ToolContext
from google.genai import types

from trends_and_insights_agent.shared_libraries.callbacks import (
    before_model_status_callback,
    before_tool_status_callback,
    after_tool_status_callback,
    reorder_parts_text_first,
    campaign_callback_function,
    rate_limit_callback,
    TOOL_STATUS_MESSAGES,
    AGENT_STATUS_MESSAGES,
    TOOL_DESCRIPTIONS,
)


class TestCallbackConstants:
    """Tests for callback constant dictionaries."""

    def test_tool_status_messages_exist(self):
        """Test that TOOL_STATUS_MESSAGES is populated."""
        assert isinstance(TOOL_STATUS_MESSAGES, dict)
        assert len(TOOL_STATUS_MESSAGES) > 0
        assert "get_daily_gtrends" in TOOL_STATUS_MESSAGES
        assert "generate_image" in TOOL_STATUS_MESSAGES
        assert "generate_video" in TOOL_STATUS_MESSAGES

    def test_agent_status_messages_exist(self):
        """Test that AGENT_STATUS_MESSAGES is populated."""
        assert isinstance(AGENT_STATUS_MESSAGES, dict)
        assert len(AGENT_STATUS_MESSAGES) > 0
        assert "root_agent" in AGENT_STATUS_MESSAGES
        assert "ad_copy_drafter" in AGENT_STATUS_MESSAGES

    def test_tool_descriptions_exist(self):
        """Test that TOOL_DESCRIPTIONS is populated."""
        assert isinstance(TOOL_DESCRIPTIONS, dict)
        assert len(TOOL_DESCRIPTIONS) > 0
        assert "google_search" in TOOL_DESCRIPTIONS


class TestBeforeModelStatusCallback:
    """Tests for before_model_status_callback."""

    def test_callback_signature(self):
        """Test that callback has correct signature."""
        # Create mock objects
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "root_agent"
        callback_context.state = {}
        llm_request = Mock(spec=LlmRequest)

        # Call should not raise
        before_model_status_callback(callback_context, llm_request)

    def test_sets_ui_status_update(self):
        """Test that callback sets ui:status_update in state."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "ad_copy_drafter"
        callback_context.state = {}
        llm_request = Mock(spec=LlmRequest)

        before_model_status_callback(callback_context, llm_request)

        assert "ui:status_update" in callback_context.state
        assert isinstance(callback_context.state["ui:status_update"], str)

    def test_known_agent_name(self):
        """Test callback with known agent name."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "root_agent"
        callback_context.state = {}
        llm_request = Mock(spec=LlmRequest)

        before_model_status_callback(callback_context, llm_request)

        expected_msg = AGENT_STATUS_MESSAGES["root_agent"]
        assert callback_context.state["ui:status_update"] == expected_msg

    def test_unknown_agent_name(self):
        """Test callback with unknown agent name."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "unknown_agent_123"
        callback_context.state = {}
        llm_request = Mock(spec=LlmRequest)

        before_model_status_callback(callback_context, llm_request)

        assert "Working on unknown_agent_123" in callback_context.state["ui:status_update"]


class TestBeforeToolStatusCallback:
    """Tests for before_tool_status_callback (async)."""

    def test_callback_signature(self):
        """Test that async callback has correct signature."""
        import asyncio

        tool = Mock(spec=BaseTool)
        tool.name = "google_search"
        args = {"query": "test query"}
        tool_context = Mock(spec=ToolContext)
        tool_context.state = {}

        result = asyncio.run(before_tool_status_callback(tool, args, tool_context))
        # Should return None
        assert result is None

    def test_sets_tool_start_time(self):
        """Test that callback tracks tool start time."""
        import asyncio

        tool = Mock(spec=BaseTool)
        tool.name = "generate_image"
        args = {}
        tool_context = Mock(spec=ToolContext)
        tool_context.state = {}

        asyncio.run(before_tool_status_callback(tool, args, tool_context))

        assert "_tool_start_ts" in tool_context.state
        assert "_tool_name" in tool_context.state
        assert tool_context.state["_tool_name"] == "generate_image"

    @patch("trends_and_insights_agent.shared_libraries.callbacks.ENABLE_LLM_STATUS", False)
    def test_static_status_message(self):
        """Test callback with LLM status disabled (static messages)."""
        import asyncio

        tool = Mock(spec=BaseTool)
        tool.name = "get_daily_gtrends"
        args = {}
        tool_context = Mock(spec=ToolContext)
        tool_context.state = {}

        asyncio.run(before_tool_status_callback(tool, args, tool_context))

        expected = TOOL_STATUS_MESSAGES["get_daily_gtrends"]
        assert tool_context.state["ui:status_update"] == expected


class TestAfterToolStatusCallback:
    """Tests for after_tool_status_callback (async)."""

    def test_callback_signature(self):
        """Test that async callback has correct signature."""
        import asyncio

        tool = Mock(spec=BaseTool)
        tool.name = "google_search"
        args = {}
        tool_context = Mock(spec=ToolContext)
        tool_context.state = {"_tool_start_ts": 123456.0, "_tool_name": "google_search"}
        tool_response = {}

        result = asyncio.run(
            after_tool_status_callback(tool, args, tool_context, tool_response)
        )
        assert result is None

    def test_logs_duration(self):
        """Test that callback logs duration (doesn't raise)."""
        import time
        import asyncio

        tool = Mock(spec=BaseTool)
        tool.name = "generate_video"
        args = {}
        tool_context = Mock(spec=ToolContext)
        tool_context.state = {"_tool_start_ts": time.time() - 1.5, "_tool_name": "generate_video"}
        tool_response = {}

        # Should not raise
        asyncio.run(after_tool_status_callback(tool, args, tool_context, tool_response))


class TestReorderPartsTextFirst:
    """Tests for reorder_parts_text_first callback."""

    def test_callback_signature(self):
        """Test that callback has correct signature."""
        callback_context = Mock(spec=CallbackContext)
        llm_response = Mock(spec=LlmResponse)
        llm_response.content = None

        result = reorder_parts_text_first(callback_context, llm_response)
        assert result is not None

    def test_no_content_returns_response(self):
        """Test callback with no content."""
        callback_context = Mock(spec=CallbackContext)
        llm_response = Mock(spec=LlmResponse)
        llm_response.content = None

        result = reorder_parts_text_first(callback_context, llm_response)
        assert result == llm_response

    def test_reorders_text_before_function_calls(self):
        """Test that text parts come before function call parts."""
        callback_context = Mock(spec=CallbackContext)
        llm_response = Mock(spec=LlmResponse)

        # Create mock parts with proper attributes
        text_part = Mock()
        text_part.text = "Some text"
        text_part.inline_data = None
        text_part.thought = False
        text_part.thought_signature = None

        func_part = Mock()
        func_part.text = None
        func_part.inline_data = None
        func_part.thought = False
        func_part.thought_signature = None

        # Start with function call first
        llm_response.content = Mock()
        llm_response.content.parts = [func_part, text_part]

        result = reorder_parts_text_first(callback_context, llm_response)

        # Verify the result has reordered parts (text should be first)
        assert len(result.content.parts) == 2
        # First part should have text
        assert result.content.parts[0].text is not None
        # Second part should have None text (function call)
        assert result.content.parts[1].text is None


class TestCampaignCallbackFunction:
    """Tests for campaign_callback_function."""

    def test_callback_signature(self):
        """Test that callback has correct signature."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "test_agent"
        callback_context.state = MagicMock()
        callback_context.state.get.return_value = None

        result = campaign_callback_function(callback_context)
        # Can return None or types.Content
        assert result is None or isinstance(result, types.Content)

    def test_initializes_missing_brand(self):
        """Test that callback initializes brand if missing."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "test_agent"
        callback_context.state = {}

        campaign_callback_function(callback_context)

        assert "brand" in callback_context.state
        assert callback_context.state["brand"] == ""

    def test_initializes_all_required_fields(self):
        """Test that callback initializes all required fields."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "test_agent"
        callback_context.state = {}

        campaign_callback_function(callback_context)

        required_fields = [
            "brand",
            "target_audience",
            "target_product",
            "key_selling_points",
            "final_select_ad_copies",
            "final_select_vis_concepts",
            "img_artifact_keys",
            "vid_artifact_keys",
            "target_search_trends",
            "target_yt_trends",
        ]

        for field in required_fields:
            assert field in callback_context.state

    def test_does_not_override_existing_values(self):
        """Test that callback doesn't override existing values."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.agent_name = "test_agent"

        # Use MagicMock for state to allow .get() calls
        callback_context.state = MagicMock()
        callback_context.state.__getitem__.side_effect = lambda k: {
            "brand": "Nike",
            "target_product": "Air Max",
        }.get(k)
        callback_context.state.get.side_effect = lambda k: {
            "brand": "Nike",
            "target_product": "Air Max",
        }.get(k)

        result = campaign_callback_function(callback_context)

        # The callback should have queried for brand and target_product
        callback_context.state.get.assert_any_call("brand")
        callback_context.state.get.assert_any_call("target_product")


class TestRateLimitCallback:
    """Tests for rate_limit_callback."""

    def test_callback_signature(self):
        """Test that callback has correct signature."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.state = {}
        llm_request = Mock(spec=LlmRequest)

        # Should not raise
        rate_limit_callback(callback_context, llm_request)

    def test_initializes_timer_on_first_call(self):
        """Test that callback initializes timer on first call."""
        callback_context = Mock(spec=CallbackContext)
        callback_context.state = {}
        llm_request = Mock(spec=LlmRequest)

        rate_limit_callback(callback_context, llm_request)

        assert "timer_start" in callback_context.state
        assert "request_count" in callback_context.state
        assert callback_context.state["request_count"] == 1

    def test_increments_request_count(self):
        """Test that callback increments request count."""
        import time

        callback_context = Mock(spec=CallbackContext)
        callback_context.state = {
            "timer_start": time.time(),
            "request_count": 5,
        }
        llm_request = Mock(spec=LlmRequest)

        rate_limit_callback(callback_context, llm_request)

        assert callback_context.state["request_count"] == 6

    @patch("time.sleep")
    def test_sleeps_when_quota_exceeded(self, mock_sleep):
        """Test that callback sleeps when quota is exceeded."""
        import time

        callback_context = Mock(spec=CallbackContext)
        # Set timer to 1 second ago, and request count over quota
        callback_context.state = {
            "timer_start": time.time() - 1,
            "request_count": 1001,  # Over default quota of 1000
        }
        llm_request = Mock(spec=LlmRequest)

        rate_limit_callback(callback_context, llm_request)

        # Should have called sleep
        assert mock_sleep.called
