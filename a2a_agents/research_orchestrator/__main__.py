"""Entry point for research_orchestrator a2a server."""

from .standalone_agent import standalone_research_orchestrator

# Export the agent for ADK to find
agent = standalone_research_orchestrator