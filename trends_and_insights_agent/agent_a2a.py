"""Root Agent with A2A Protocol Integration.

This is the main orchestrator agent that consumes a2a server agents
for trends analysis, research orchestration, and ad content generation.
"""

import os
import logging
from typing import Dict, Any, Optional

from google.genai import types
from google.adk.agents import Agent
from google.adk.a2a import A2AClient
from google.adk.tools import load_artifacts

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import GLOBAL_INSTR, ROOT_AGENT_INSTR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class A2AAgentConnector:
    """Manages connections to a2a server agents."""
    
    def __init__(self):
        # Get base URL from environment or use defaults
        self.base_url = os.getenv("A2A_BASE_URL", "http://localhost")
        self.base_port = int(os.getenv("A2A_BASE_PORT", "9000"))
        
        # Initialize a2a clients
        self.research_client = None
        self.trends_client = None
        self.ad_client = None
        
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize a2a client connections."""
        try:
            # Research Orchestrator
            self.research_client = A2AClient(
                url=f"{self.base_url}:{self.base_port}",
                name="research_orchestrator",
            )
            logger.info(f"Connected to research_orchestrator at {self.base_url}:{self.base_port}")
            
            # Trends and Insights
            self.trends_client = A2AClient(
                url=f"{self.base_url}:{self.base_port + 1}",
                name="trends_insights",
            )
            logger.info(f"Connected to trends_insights at {self.base_url}:{self.base_port + 1}")
            
            # Ad Content Generator
            self.ad_client = A2AClient(
                url=f"{self.base_url}:{self.base_port + 2}",
                name="ad_generator",
            )
            logger.info(f"Connected to ad_generator at {self.base_url}:{self.base_port + 2}")
            
        except Exception as e:
            logger.error(f"Failed to initialize a2a clients: {e}")
            raise
            
    async def invoke_trends_agent(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the trends and insights a2a agent."""
        if not self.trends_client:
            raise RuntimeError("Trends client not initialized")
            
        request = {
            "user_message": session_state.get("user_message", ""),
            "uploaded_files": session_state.get("uploaded_files", []),
            "selected_trend": session_state.get("selected_trend"),
        }
        
        response = await self.trends_client.invoke(request)
        return response
        
    async def invoke_research_agent(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the research orchestrator a2a agent."""
        if not self.research_client:
            raise RuntimeError("Research client not initialized")
            
        request = {
            "target_search_trends": session_state.get("target_search_trends"),
            "target_yt_trends": session_state.get("target_yt_trends"),
            "target_product": session_state.get("target_product"),
            "target_audience": session_state.get("target_audience"),
            "campaign_guide_data": session_state.get("campaign_guide_data"),
        }
        
        response = await self.research_client.invoke(request)
        return response
        
    async def invoke_ad_agent(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the ad content generator a2a agent."""
        if not self.ad_client:
            raise RuntimeError("Ad generator client not initialized")
            
        request = {
            "draft_report": session_state.get("draft_report"),
            "target_product": session_state.get("target_product"),
            "target_audience": session_state.get("target_audience"),
            "campaign_guide_data": session_state.get("campaign_guide_data"),
            "target_search_trends": session_state.get("target_search_trends"),
            "target_yt_trends": session_state.get("target_yt_trends"),
            "creative_brief": session_state.get("creative_brief"),
        }
        
        response = await self.ad_client.invoke(request)
        return response


# Initialize a2a connector
a2a_connector = A2AAgentConnector()


# Custom tool functions that wrap a2a invocations
async def invoke_trends_insights(session_state: Dict[str, Any]) -> Dict[str, Any]:
    """Tool function to invoke trends and insights agent via a2a."""
    logger.info("Invoking trends_insights agent via a2a")
    result = await a2a_connector.invoke_trends_agent(session_state)
    logger.info(f"Received response from trends_insights: {list(result.keys())}")
    return result


async def invoke_research_orchestrator(session_state: Dict[str, Any]) -> Dict[str, Any]:
    """Tool function to invoke research orchestrator agent via a2a."""
    logger.info("Invoking research_orchestrator agent via a2a")
    result = await a2a_connector.invoke_research_agent(session_state)
    logger.info(f"Received response from research_orchestrator: {list(result.keys())}")
    return result


async def invoke_ad_generator(session_state: Dict[str, Any]) -> Dict[str, Any]:
    """Tool function to invoke ad generator agent via a2a."""
    logger.info("Invoking ad_generator agent via a2a")
    result = await a2a_connector.invoke_ad_agent(session_state)
    logger.info(f"Received response from ad_generator: {list(result.keys())}")
    return result


# Root agent with a2a integration
root_agent_a2a = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant orchestrating multiple specialized agents via a2a protocol.",
    instruction=f"""{ROOT_AGENT_INSTR}
    
    You coordinate with three specialized a2a agents:
    
    1. **trends_insights**: Handles trend selection and campaign data extraction
       - Invoke when user uploads PDFs or requests trend analysis
       - Returns: target trends, campaign data, initial insights
    
    2. **research_orchestrator**: Performs comprehensive multi-source research
       - Invoke after trends are selected and campaign data is extracted
       - Returns: consolidated research report with citations
    
    3. **ad_generator**: Creates comprehensive ad campaigns with media
       - Invoke after research is complete
       - Returns: ad copy, visual concepts, generated images/videos
    
    Workflow:
    1. Start with greeting and guide user through PDF upload and trend selection
    2. Invoke trends_insights agent for data extraction and trend analysis
    3. Invoke research_orchestrator for comprehensive research
    4. Invoke ad_generator for creative campaign generation
    5. Compile and present final report with all assets
    
    Use the session state to pass data between agent invocations.
    """,
    global_instruction=GLOBAL_INSTR,
    tools=[
        invoke_trends_insights,
        invoke_research_orchestrator,
        invoke_ad_generator,
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        response_modalities=["TEXT"],
    ),
    before_agent_callback=[
        callbacks._load_session_state,
        callbacks.before_agent_get_user_file,
    ],
    before_model_callback=callbacks.rate_limit_callback,
)