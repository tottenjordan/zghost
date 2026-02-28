"""
Tests for Memory Bank integration: save_session_to_memory_callback,
root_agent after_agent_callback wiring, and preload_memory tool presence.
"""

import asyncio
import os
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Environment setup — must happen before any project imports
# ---------------------------------------------------------------------------
os.environ.setdefault("BUCKET", "gs://test-bucket")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT_NUMBER", "123456")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("YT_SECRET_MNGR_NAME", "test-secret")


class TestSaveSessionToMemoryCallback:
    """Tests for the save_session_to_memory_callback function."""

    def test_callback_exists(self):
        from trends_and_insights_agent.shared_libraries.callbacks import (
            save_session_to_memory_callback,
        )
        assert callable(save_session_to_memory_callback)

    def test_callback_is_async(self):
        from trends_and_insights_agent.shared_libraries.callbacks import (
            save_session_to_memory_callback,
        )
        assert asyncio.iscoroutinefunction(save_session_to_memory_callback)

    def test_handles_none_memory_service(self):
        """When memory_service is None, callback should complete without error."""
        from trends_and_insights_agent.shared_libraries.callbacks import (
            save_session_to_memory_callback,
        )

        mock_context = mock.MagicMock()
        mock_context._invocation_context.memory_service = None

        # Should not raise
        asyncio.get_event_loop().run_until_complete(
            save_session_to_memory_callback(mock_context)
        )

    def test_calls_add_session_to_memory(self):
        """When memory_service is present, should call add_session_to_memory."""
        from trends_and_insights_agent.shared_libraries.callbacks import (
            save_session_to_memory_callback,
        )

        mock_memory_service = mock.AsyncMock()
        mock_session = mock.MagicMock()

        mock_context = mock.MagicMock()
        mock_context._invocation_context.memory_service = mock_memory_service
        mock_context._invocation_context.session = mock_session

        asyncio.get_event_loop().run_until_complete(
            save_session_to_memory_callback(mock_context)
        )

        mock_memory_service.add_session_to_memory.assert_awaited_once_with(
            mock_session
        )

    def test_handles_memory_service_error_gracefully(self):
        """If add_session_to_memory raises, callback should log warning, not crash."""
        from trends_and_insights_agent.shared_libraries.callbacks import (
            save_session_to_memory_callback,
        )

        mock_memory_service = mock.AsyncMock()
        mock_memory_service.add_session_to_memory.side_effect = RuntimeError(
            "Memory service unavailable"
        )

        mock_context = mock.MagicMock()
        mock_context._invocation_context.memory_service = mock_memory_service
        mock_context._invocation_context.session = mock.MagicMock()

        # Should not raise
        asyncio.get_event_loop().run_until_complete(
            save_session_to_memory_callback(mock_context)
        )


class TestRootAgentMemoryWiring:
    """Tests that root_agent is correctly wired with memory callbacks and tools."""

    def test_root_agent_has_after_agent_callback(self):
        from trends_and_insights_agent.agent import root_agent
        from trends_and_insights_agent.shared_libraries.callbacks import (
            save_session_to_memory_callback,
        )

        assert root_agent.after_agent_callback is not None
        assert root_agent.after_agent_callback == save_session_to_memory_callback

    def test_root_agent_has_preload_memory_tool(self):
        from trends_and_insights_agent.agent import root_agent
        from google.adk.tools import preload_memory

        assert preload_memory in root_agent.tools
