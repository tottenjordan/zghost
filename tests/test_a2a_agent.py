"""Tests for A2A agent card generation.

Validates that the root_agent can produce a well-formed A2A agent card
with required fields (name, description, skills).
"""

import os
import pytest

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"


def test_agent_card_builds():
    """Agent card should build with name, description, and skills."""
    from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
    from trends_and_insights_agent.agent import root_agent

    builder = AgentCardBuilder(agent=root_agent, url="http://localhost:8080")
    card = builder.build()

    assert card.name, "Agent card must have a name"
    assert card.description, "Agent card must have a description"
    assert card.url == "http://localhost:8080"
    assert card.skills is not None, "Agent card must have skills"
    assert len(card.skills) > 0, "Agent card must have at least one skill"


def test_agent_card_skill_names():
    """Each skill in the agent card should have a name and description."""
    from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
    from trends_and_insights_agent.agent import root_agent

    builder = AgentCardBuilder(agent=root_agent, url="http://localhost:8080")
    card = builder.build()

    for skill in card.skills:
        assert skill.name, f"Skill must have a name: {skill}"
        assert skill.description, f"Skill '{skill.name}' must have a description"


def test_to_a2a_creates_app():
    """to_a2a should return a Starlette ASGI application."""
    from google.adk.a2a.utils.agent_to_a2a import to_a2a
    from trends_and_insights_agent.agent import root_agent

    app = to_a2a(root_agent, host="0.0.0.0", port=8080)
    assert app is not None, "to_a2a must return an ASGI app"
