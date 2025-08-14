"""Entry point for ad_generator a2a server."""

from .standalone_agent import standalone_ad_generator

# Export the agent for ADK to find
agent = standalone_ad_generator