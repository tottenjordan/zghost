"""A2A Client Implementation for connecting to external a2a server agents.

This module provides client functionality to connect to a2a server agents
running on different ports.
"""

import json
import logging
from typing import Dict, Any, Optional
import requests
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class A2AClient:
    """Client for connecting to a2a server agents."""
    
    def __init__(self, base_url: str, agent_name: str, timeout: int = 300):
        """Initialize a2a client.
        
        Args:
            base_url: Base URL of the a2a server (e.g., http://localhost:9000)
            agent_name: Name of the agent
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.agent_name = agent_name
        self.timeout = timeout
        self.session = requests.Session()
        
        # Test connection and get agent card
        self.agent_card = self._get_agent_card()
        
    def _get_agent_card(self) -> Dict[str, Any]:
        """Fetch the agent card from the server."""
        try:
            url = urljoin(self.base_url, "/agent-card")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get agent card from {self.agent_name}: {e}")
            raise ConnectionError(f"Cannot connect to {self.agent_name} at {self.base_url}")
            
    def invoke(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the a2a agent with the given request.
        
        Args:
            request_data: Request payload to send to the agent
            
        Returns:
            Response from the agent
        """
        try:
            url = urljoin(self.base_url, "/invoke")
            
            # Send request to a2a server
            response = self.session.post(
                url,
                json=request_data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            logger.info(f"Received response from {self.agent_name}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Request to {self.agent_name} timed out")
            raise TimeoutError(f"Request to {self.agent_name} timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to {self.agent_name} failed: {e}")
            raise RuntimeError(f"Failed to invoke {self.agent_name}: {e}")
            
    def health_check(self) -> bool:
        """Check if the a2a server is healthy."""
        try:
            url = urljoin(self.base_url, "/health")
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False


class A2AClientManager:
    """Manages multiple a2a client connections."""
    
    def __init__(self, base_port: int = 9000, host: str = "localhost"):
        """Initialize the client manager.
        
        Args:
            base_port: Base port for a2a servers
            host: Host where a2a servers are running
        """
        self.base_port = base_port
        self.host = host
        self.clients: Dict[str, A2AClient] = {}
        
    def connect_agent(self, agent_name: str, port_offset: int) -> A2AClient:
        """Connect to an a2a agent server.
        
        Args:
            agent_name: Name of the agent
            port_offset: Offset from base port
            
        Returns:
            Connected a2a client
        """
        port = self.base_port + port_offset
        base_url = f"http://{self.host}:{port}"
        
        try:
            client = A2AClient(base_url, agent_name)
            self.clients[agent_name] = client
            logger.info(f"Connected to {agent_name} at {base_url}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to {agent_name}: {e}")
            raise
            
    def get_client(self, agent_name: str) -> Optional[A2AClient]:
        """Get a connected client by agent name."""
        return self.clients.get(agent_name)
        
    def connect_all_agents(self):
        """Connect to all standard a2a agents."""
        agents = [
            ("research_orchestrator", 0),
            ("trends_insights", 1),
            ("ad_generator", 2),
        ]
        
        for agent_name, port_offset in agents:
            try:
                self.connect_agent(agent_name, port_offset)
            except Exception as e:
                logger.warning(f"Could not connect to {agent_name}: {e}")
                
    def health_check_all(self) -> Dict[str, bool]:
        """Check health of all connected agents."""
        results = {}
        for name, client in self.clients.items():
            results[name] = client.health_check()
        return results