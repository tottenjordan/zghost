#!/usr/bin/env python3
"""A2A Server Runner for Marketing Intelligence Agents.

This script runs multiple a2a server agents that can be consumed by the root orchestrator.
Each agent runs on a different port and exposes its capabilities via the a2a protocol.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from google.adk.a2a import A2AServer, AgentCard
from google.adk.agents import Agent

# Import our a2a agents
from a2a_agents.remote_a2a.research_orchestrator import research_orchestrator_agent
from a2a_agents.remote_a2a.research_orchestrator.agent import AGENT_CARD as RESEARCH_CARD
from a2a_agents.remote_a2a.trends_insights import trends_insights_agent
from a2a_agents.remote_a2a.trends_insights.agent import AGENT_CARD as TRENDS_CARD
from a2a_agents.remote_a2a.ad_generator import ad_generator_agent
from a2a_agents.remote_a2a.ad_generator.agent import AGENT_CARD as AD_CARD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class A2AAgentServer:
    """Manages an individual a2a server agent."""
    
    def __init__(
        self,
        agent: Agent,
        agent_card: AgentCard,
        port: int,
        host: str = "0.0.0.0"
    ):
        self.agent = agent
        self.agent_card = agent_card
        self.port = port
        self.host = host
        self.server = None
        
    async def start(self):
        """Start the a2a server."""
        try:
            self.server = A2AServer(
                agent=self.agent,
                agent_card=self.agent_card,
                host=self.host,
                port=self.port,
            )
            logger.info(f"Starting {self.agent.name} on {self.host}:{self.port}")
            await self.server.start()
        except Exception as e:
            logger.error(f"Failed to start {self.agent.name}: {e}")
            raise
            
    async def stop(self):
        """Stop the a2a server."""
        if self.server:
            await self.server.stop()
            logger.info(f"Stopped {self.agent.name}")


class A2AServerManager:
    """Manages multiple a2a server agents."""
    
    def __init__(self):
        self.servers: List[A2AAgentServer] = []
        self.setup_servers()
        
    def setup_servers(self):
        """Configure all a2a servers."""
        # Get base port from environment or use default
        base_port = int(os.getenv("A2A_BASE_PORT", "9000"))
        
        # Configure each agent server
        self.servers = [
            A2AAgentServer(
                agent=research_orchestrator_agent,
                agent_card=RESEARCH_CARD,
                port=base_port,
            ),
            A2AAgentServer(
                agent=trends_insights_agent,
                agent_card=TRENDS_CARD,
                port=base_port + 1,
            ),
            A2AAgentServer(
                agent=ad_generator_agent,
                agent_card=AD_CARD,
                port=base_port + 2,
            ),
        ]
        
    async def start_all(self):
        """Start all a2a servers."""
        logger.info("Starting all a2a server agents...")
        tasks = [server.start() for server in self.servers]
        await asyncio.gather(*tasks)
        logger.info("All a2a servers started successfully")
        
    async def stop_all(self):
        """Stop all a2a servers."""
        logger.info("Stopping all a2a server agents...")
        tasks = [server.stop() for server in self.servers]
        await asyncio.gather(*tasks)
        logger.info("All a2a servers stopped")
        
    def print_server_info(self):
        """Print information about running servers."""
        print("\n" + "="*60)
        print("A2A SERVER AGENTS RUNNING")
        print("="*60)
        for server in self.servers:
            print(f"\n{server.agent.name}:")
            print(f"  URL: http://{server.host}:{server.port}")
            print(f"  Agent Card: http://{server.host}:{server.port}/agent-card")
            print(f"  Description: {server.agent_card.description}")
        print("\n" + "="*60)
        print("Press Ctrl+C to stop all servers")
        print("="*60 + "\n")


async def main():
    """Main entry point for a2a server runner."""
    manager = A2AServerManager()
    
    try:
        # Start all servers
        await manager.start_all()
        manager.print_server_info()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Clean shutdown
        await manager.stop_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)