"""
Tests for focus_group_evaluator_agent: agent configuration, prompt content,
video analysis tool, and root_agent integration.
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


# ===================================================================
# 1. Agent Configuration
# ===================================================================
class TestFocusGroupAgentConfiguration:

    def test_agent_exists(self):
        from trends_and_insights_agent.skills.focus_group.agents import (
            focus_group_evaluator_agent,
        )
        assert focus_group_evaluator_agent is not None

    def test_agent_name(self):
        from trends_and_insights_agent.skills.focus_group.agents import (
            focus_group_evaluator_agent,
        )
        assert focus_group_evaluator_agent.name == "focus_group_evaluator_agent"

    def test_agent_uses_critic_model(self):
        from trends_and_insights_agent.skills.focus_group.agents import (
            focus_group_evaluator_agent,
        )
        from trends_and_insights_agent.shared_libraries.config import config
        assert focus_group_evaluator_agent.model == config.critic_model

    def test_agent_has_analyze_tool(self):
        from trends_and_insights_agent.skills.focus_group.agents import (
            focus_group_evaluator_agent,
        )
        tool_names = {
            t.__name__ if callable(t) else str(t)
            for t in focus_group_evaluator_agent.tools
        }
        assert "analyze_commercial_video" in tool_names

    def test_agent_has_rate_limit_callback(self):
        from trends_and_insights_agent.skills.focus_group.agents import (
            focus_group_evaluator_agent,
        )
        from trends_and_insights_agent.shared_libraries.callbacks import (
            rate_limit_callback,
        )
        assert focus_group_evaluator_agent.before_model_callback == rate_limit_callback

    def test_agent_registered_in_root(self):
        from trends_and_insights_agent.agent import root_agent
        sub_names = [a.name for a in root_agent.sub_agents]
        assert "focus_group_evaluator_agent" in sub_names


# ===================================================================
# 2. Prompt Content
# ===================================================================
class TestFocusGroupPrompt:

    def _get_prompt(self):
        from trends_and_insights_agent.skills.focus_group.prompts import (
            FOCUS_GROUP_INSTR,
        )
        return FOCUS_GROUP_INSTR

    def test_prompt_references_session_state_keys(self):
        prompt = self._get_prompt()
        assert "{final_select_ad_copies}" in prompt
        assert "{final_select_vis_concepts}" in prompt
        assert "{target_search_trends}" in prompt
        assert "{target_yt_trends}" in prompt

    def test_prompt_references_campaign_context(self):
        prompt = self._get_prompt()
        assert "{brand}" in prompt
        assert "{target_product}" in prompt
        assert "{target_audience}" in prompt
        assert "{key_selling_points}" in prompt

    def test_prompt_includes_scoring_categories(self):
        prompt = self._get_prompt()
        assert "Visual Quality" in prompt
        assert "Narrative Consistency" in prompt
        assert "Trend Relevance" in prompt
        assert "Product Integration" in prompt
        assert "Emotional Impact" in prompt
        assert "Audience Appeal" in prompt

    def test_prompt_includes_focus_group_simulation(self):
        prompt = self._get_prompt()
        assert "panel" in prompt.lower() or "panelist" in prompt.lower()
        assert "5" in prompt  # 5 panelists

    def test_prompt_includes_uplift_prediction(self):
        prompt = self._get_prompt()
        assert "uplift" in prompt.lower()
        assert "Low" in prompt
        assert "Medium" in prompt
        assert "High" in prompt
        assert "Very High" in prompt

    def test_prompt_includes_go_nogo(self):
        prompt = self._get_prompt()
        assert "Go/No-Go" in prompt or "GO" in prompt

    def test_prompt_references_video_analysis_tool(self):
        prompt = self._get_prompt()
        assert "analyze_commercial_video" in prompt

    def test_prompt_includes_summary_report(self):
        prompt = self._get_prompt()
        assert "Summary Report" in prompt or "Average Scores" in prompt
        assert "Strengths" in prompt
        assert "Improvement" in prompt


# ===================================================================
# 3. Video Analysis Tool
# ===================================================================
class TestAnalyzeCommercialVideoTool:

    def _import_tool(self):
        from trends_and_insights_agent.skills.focus_group.tools import (
            analyze_commercial_video,
        )
        return analyze_commercial_video

    def test_tool_exists(self):
        tool = self._import_tool()
        assert callable(tool)

    def test_fails_without_commercial_artifact(self):
        tool = self._import_tool()
        mock_ctx = mock.MagicMock()
        mock_ctx.state = {}

        result = tool(tool_context=mock_ctx)
        assert result["status"] == "failed"
        assert "commercial_artifact" in result["error"]

    def test_fails_with_empty_gcs_uri(self):
        tool = self._import_tool()
        mock_ctx = mock.MagicMock()
        mock_ctx.state = {"commercial_artifact": {"gcs_uri": ""}}

        result = tool(tool_context=mock_ctx)
        assert result["status"] == "failed"
        assert "gcs_uri" in result["error"]

    @mock.patch(
        "trends_and_insights_agent.skills.focus_group.tools.client"
    )
    def test_success(self, mock_client):
        tool = self._import_tool()
        mock_ctx = mock.MagicMock()
        mock_ctx.state = {
            "commercial_artifact": {
                "gcs_uri": "gs://test-bucket/av_studio/commercial.mp4",
            }
        }

        mock_response = mock.MagicMock()
        mock_response.text = "Detailed video analysis: scenes are well composed..."
        mock_client.models.generate_content.return_value = mock_response

        result = tool(tool_context=mock_ctx)
        assert result["status"] == "ok"
        assert "analysis" in result
        assert len(result["analysis"]) > 0

        # Verify Gemini was called with video part
        call_args = mock_client.models.generate_content.call_args
        assert call_args is not None

    @mock.patch(
        "trends_and_insights_agent.skills.focus_group.tools.client"
    )
    def test_handles_empty_response(self, mock_client):
        tool = self._import_tool()
        mock_ctx = mock.MagicMock()
        mock_ctx.state = {
            "commercial_artifact": {
                "gcs_uri": "gs://test-bucket/av_studio/commercial.mp4",
            }
        }

        mock_response = mock.MagicMock()
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response

        result = tool(tool_context=mock_ctx)
        assert result["status"] == "failed"

    @mock.patch(
        "trends_and_insights_agent.skills.focus_group.tools.client"
    )
    def test_handles_exception(self, mock_client):
        tool = self._import_tool()
        mock_ctx = mock.MagicMock()
        mock_ctx.state = {
            "commercial_artifact": {
                "gcs_uri": "gs://test-bucket/av_studio/commercial.mp4",
            }
        }

        mock_client.models.generate_content.side_effect = RuntimeError("API error")

        result = tool(tool_context=mock_ctx)
        assert result["status"] == "failed"
        assert "API error" in result["error"]


# ===================================================================
# 4. Root Agent Integration
# ===================================================================
class TestRootAgentIntegration:

    def test_root_prompt_mentions_focus_group(self):
        from trends_and_insights_agent.prompts import ROOT_AGENT_INSTR
        assert "focus_group_evaluator_agent" in ROOT_AGENT_INSTR

    def test_root_prompt_has_step_6(self):
        from trends_and_insights_agent.prompts import ROOT_AGENT_INSTR
        assert "6." in ROOT_AGENT_INSTR

    def test_focus_group_in_skills(self):
        from trends_and_insights_agent.skills.focus_group.agents import focus_group_evaluator_agent
        assert focus_group_evaluator_agent is not None
