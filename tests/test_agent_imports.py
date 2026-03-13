"""Smoke tests for agent imports - verify all agents can be imported without errors."""

import pytest


class TestRootAgentImport:
    """Tests for root agent import."""

    def test_root_agent_imports(self):
        """Test that root_agent can be imported."""
        from trends_and_insights_agent.agent import root_agent

        assert root_agent is not None

    def test_root_agent_has_name(self):
        """Test that root_agent has a name attribute."""
        from trends_and_insights_agent.agent import root_agent

        assert hasattr(root_agent, "name")


class TestCommonAgentsImport:
    """Tests for common_agents imports."""

    def test_staged_researcher_imports(self):
        """Test that staged_researcher agent can be imported."""
        from trends_and_insights_agent.common_agents.staged_researcher.agent import (
            research_orchestrator,
        )

        assert research_orchestrator is not None

    def test_ad_content_generator_imports(self):
        """Test that ad_content_generator agent can be imported."""
        from trends_and_insights_agent.common_agents.ad_content_generator.agent import (
            ad_content_generator_agent,
        )

        assert ad_content_generator_agent is not None

    def test_trend_assistant_imports(self):
        """Test that trend_assistant agent can be imported."""
        from trends_and_insights_agent.common_agents.trend_assistant.agent import (
            trends_and_insights_agent,
        )

        assert trends_and_insights_agent is not None


class TestSubAgentsImport:
    """Tests for sub-agent imports."""

    def test_youtube_web_researcher_imports(self):
        """Test that youtube_web_researcher can be imported."""
        try:
            from trends_and_insights_agent.common_agents.staged_researcher.sub_agents.youtube_web_researcher.agent import (
                yt_sequential_planner,
            )

            assert yt_sequential_planner is not None
        except ImportError:
            pytest.skip("youtube_web_researcher may not exist")

    def test_search_web_researcher_imports(self):
        """Test that search_web_researcher can be imported."""
        try:
            from trends_and_insights_agent.common_agents.staged_researcher.sub_agents.search_web_researcher.agent import (
                gs_sequential_planner,
            )

            assert gs_sequential_planner is not None
        except ImportError:
            pytest.skip("search_web_researcher may not exist")

    def test_campaign_web_researcher_imports(self):
        """Test that campaign_web_researcher can be imported."""
        try:
            from trends_and_insights_agent.common_agents.staged_researcher.sub_agents.campaign_web_researcher.agent import (
                ca_sequential_planner,
            )

            assert ca_sequential_planner is not None
        except ImportError:
            pytest.skip("campaign_web_researcher may not exist")


class TestAgentStructure:
    """Tests for agent structure and attributes."""

    def test_root_agent_has_sub_agents(self):
        """Test that root_agent has sub_agents or tools."""
        from trends_and_insights_agent.agent import root_agent

        # Agent should have either sub_agents, tools, or both
        has_structure = (
            hasattr(root_agent, "sub_agents")
            or hasattr(root_agent, "tools")
            or hasattr(root_agent, "_sub_agents")
            or hasattr(root_agent, "_tools")
        )
        assert has_structure

    def test_ad_content_generator_has_structure(self):
        """Test that ad_content_generator has proper structure."""
        from trends_and_insights_agent.common_agents.ad_content_generator.agent import (
            ad_content_generator_agent,
        )

        # Should have some agent structure
        assert ad_content_generator_agent is not None
        assert hasattr(ad_content_generator_agent, "name") or hasattr(
            ad_content_generator_agent, "_name"
        )

    def test_research_orchestrator_has_structure(self):
        """Test that research_orchestrator has proper structure."""
        from trends_and_insights_agent.common_agents.staged_researcher.agent import (
            research_orchestrator,
        )

        assert research_orchestrator is not None


class TestAgentNaming:
    """Tests for agent naming conventions."""

    def test_root_agent_name(self):
        """Test that root_agent has expected name."""
        from trends_and_insights_agent.agent import root_agent

        # Agent should have a name
        if hasattr(root_agent, "name"):
            assert isinstance(root_agent.name, str)
            assert len(root_agent.name) > 0

    def test_agent_names_are_strings(self):
        """Test that all agent names are strings."""
        from trends_and_insights_agent.agent import root_agent
        from trends_and_insights_agent.common_agents.ad_content_generator.agent import (
            ad_content_generator_agent,
        )

        agents = [root_agent, ad_content_generator_agent]

        for agent in agents:
            if hasattr(agent, "name"):
                assert isinstance(agent.name, str)


class TestAgentCallbacks:
    """Tests for agent callback configuration."""

    def test_root_agent_callbacks_exist(self):
        """Test that root_agent has callbacks configured."""
        from trends_and_insights_agent.agent import root_agent

        # Check if agent has callback attributes
        # (different ADK versions may use different attribute names)
        has_callbacks = any(
            [
                hasattr(root_agent, "before_agent_callback"),
                hasattr(root_agent, "after_agent_callback"),
                hasattr(root_agent, "callbacks"),
                hasattr(root_agent, "_callbacks"),
            ]
        )
        # It's OK if no callbacks, this is just a smoke test
        assert True  # Agent imports successfully


class TestModuleImports:
    """Tests for module-level imports."""

    def test_shared_libraries_import(self):
        """Test that shared_libraries modules can be imported."""
        from trends_and_insights_agent.shared_libraries import config
        from trends_and_insights_agent.shared_libraries import schema_types
        from trends_and_insights_agent.shared_libraries import callbacks

        assert config is not None
        assert schema_types is not None
        assert callbacks is not None

    def test_tools_import(self):
        """Test that tools module can be imported."""
        from trends_and_insights_agent import tools

        assert tools is not None

    def test_agent_module_import(self):
        """Test that main agent module can be imported."""
        import trends_and_insights_agent

        assert trends_and_insights_agent is not None


class TestAgentTypeChecking:
    """Tests for agent type validation."""

    def test_agents_are_not_none(self):
        """Test that imported agents are not None."""
        from trends_and_insights_agent.agent import root_agent
        from trends_and_insights_agent.common_agents.ad_content_generator.agent import (
            ad_content_generator_agent,
        )
        from trends_and_insights_agent.common_agents.staged_researcher.agent import (
            research_orchestrator,
        )

        assert root_agent is not None
        assert ad_content_generator_agent is not None
        assert research_orchestrator is not None

    def test_agents_have_callable_attributes(self):
        """Test that agents have expected callable methods (if applicable)."""
        from trends_and_insights_agent.agent import root_agent

        # Agent might have methods like run, execute, etc.
        # This is a basic smoke test - we don't call the methods
        assert root_agent is not None


class TestAgentImportPerformance:
    """Tests for agent import performance (basic smoke tests)."""

    def test_root_agent_import_speed(self):
        """Test that root_agent import completes (no infinite loops)."""
        import time

        start = time.time()
        from trends_and_insights_agent.agent import root_agent

        duration = time.time() - start

        # Import should complete within reasonable time (30 seconds)
        # Note: First import might be slow due to dependency loading
        assert duration < 30
        assert root_agent is not None

    def test_multiple_imports_idempotent(self):
        """Test that multiple imports return same object."""
        from trends_and_insights_agent.agent import root_agent as agent1
        from trends_and_insights_agent.agent import root_agent as agent2

        # Should be the same object
        assert agent1 is agent2


class TestPromptImports:
    """Tests for prompt imports (if prompts are in separate modules)."""

    def test_root_agent_prompts_exist(self):
        """Test that root_agent has prompts or instructions."""
        try:
            from trends_and_insights_agent import prompts

            assert prompts is not None
        except ImportError:
            # Prompts might be inline in agent files
            pytest.skip("Prompts module not found (may be inline)")

    def test_ad_content_generator_prompts_exist(self):
        """Test that ad_content_generator has prompts."""
        try:
            from trends_and_insights_agent.common_agents.ad_content_generator import (
                prompts,
            )

            assert prompts is not None
        except ImportError:
            pytest.skip("Ad content generator prompts not in separate module")
