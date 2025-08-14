"""Entry point for trends_insights a2a server."""

from .standalone_agent import standalone_trends_insights

# Export the agent for ADK to find
agent = standalone_trends_insights