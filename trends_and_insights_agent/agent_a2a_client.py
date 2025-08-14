"""Root Agent with A2A Client Integration.

This version connects to external a2a server agents using HTTP requests.
"""

import os
import logging
from typing import Dict, Any

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import load_artifacts, FunctionTool

from .shared_libraries import callbacks
from .shared_libraries.config import config
from .prompts import GLOBAL_INSTR, ROOT_AGENT_INSTR
from .a2a_client import A2AClientManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize a2a client manager
client_manager = A2AClientManager(
    base_port=int(os.getenv("A2A_BASE_PORT", "9000")),
    host=os.getenv("A2A_HOST", "localhost")
)

# Try to connect to all agents
client_manager.connect_all_agents()


def invoke_trends_insights(
    user_message: str,
    uploaded_files: list = None,
    selected_trend: str = None
) -> Dict[str, Any]:
    """Invoke the trends and insights a2a agent.
    
    Args:
        user_message: User's message or request
        uploaded_files: List of uploaded file paths
        selected_trend: User's selected trend
        
    Returns:
        Response from trends insights agent
    """
    client = client_manager.get_client("trends_insights")
    if not client:
        raise RuntimeError("Trends insights agent not available")
        
    request = {
        "user_message": user_message,
        "uploaded_files": uploaded_files or [],
        "selected_trend": selected_trend,
    }
    
    logger.info("Invoking trends_insights agent via a2a")
    result = client.invoke(request)
    logger.info(f"Received response with keys: {list(result.keys())}")
    return result


def invoke_research_orchestrator(
    target_search_trends: Dict[str, Any],
    target_yt_trends: Dict[str, Any],
    target_product: str,
    target_audience: str,
    campaign_guide_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Invoke the research orchestrator a2a agent.
    
    Args:
        target_search_trends: Google Search trends to research
        target_yt_trends: YouTube trends to research
        target_product: Product being marketed
        target_audience: Target audience
        campaign_guide_data: Campaign guide information
        
    Returns:
        Response from research orchestrator
    """
    client = client_manager.get_client("research_orchestrator")
    if not client:
        raise RuntimeError("Research orchestrator agent not available")
        
    request = {
        "target_search_trends": target_search_trends,
        "target_yt_trends": target_yt_trends,
        "target_product": target_product,
        "target_audience": target_audience,
        "campaign_guide_data": campaign_guide_data,
    }
    
    logger.info("Invoking research_orchestrator agent via a2a")
    result = client.invoke(request)
    logger.info(f"Received response with keys: {list(result.keys())}")
    return result


def invoke_ad_generator(
    draft_report: str,
    target_product: str,
    target_audience: str,
    campaign_guide_data: Dict[str, Any],
    target_search_trends: Dict[str, Any],
    target_yt_trends: Dict[str, Any],
    creative_brief: str = None
) -> Dict[str, Any]:
    """Invoke the ad content generator a2a agent.
    
    Args:
        draft_report: Research report with insights
        target_product: Product being marketed
        target_audience: Target audience
        campaign_guide_data: Campaign guide information
        target_search_trends: Google Search trends
        target_yt_trends: YouTube trends
        creative_brief: Optional creative brief
        
    Returns:
        Response from ad generator
    """
    client = client_manager.get_client("ad_generator")
    if not client:
        raise RuntimeError("Ad generator agent not available")
        
    request = {
        "draft_report": draft_report,
        "target_product": target_product,
        "target_audience": target_audience,
        "campaign_guide_data": campaign_guide_data,
        "target_search_trends": target_search_trends,
        "target_yt_trends": target_yt_trends,
        "creative_brief": creative_brief,
    }
    
    logger.info("Invoking ad_generator agent via a2a")
    result = client.invoke(request)
    logger.info(f"Received response with keys: {list(result.keys())}")
    return result


def check_a2a_agents_health() -> Dict[str, bool]:
    """Check the health status of all a2a agents.
    
    Returns:
        Dictionary of agent names to health status
    """
    return client_manager.health_check_all()


# Create FunctionTools for the a2a invocations
trends_tool = FunctionTool(
    function=invoke_trends_insights,
    name="invoke_trends_insights",
    description="Invoke trends and insights agent for trend selection and campaign data extraction"
)

research_tool = FunctionTool(
    function=invoke_research_orchestrator,
    name="invoke_research_orchestrator",
    description="Invoke research orchestrator for comprehensive multi-source research"
)

ad_tool = FunctionTool(
    function=invoke_ad_generator,
    name="invoke_ad_generator",
    description="Invoke ad generator for creative campaign generation"
)

health_tool = FunctionTool(
    function=check_a2a_agents_health,
    name="check_a2a_agents_health",
    description="Check health status of all a2a agents"
)


# Enhanced instruction for a2a client usage
A2A_CLIENT_INSTRUCTION = f"""{ROOT_AGENT_INSTR}

You coordinate with three specialized a2a server agents via HTTP:

1. **invoke_trends_insights**: Handles trend selection and campaign data extraction
   - Use when: User uploads PDFs or requests trend analysis
   - Parameters: user_message, uploaded_files (optional), selected_trend (optional)
   - Returns: target trends, campaign data, initial insights

2. **invoke_research_orchestrator**: Performs comprehensive multi-source research
   - Use when: After trends are selected and campaign data is extracted
   - Parameters: target_search_trends, target_yt_trends, target_product, target_audience, campaign_guide_data
   - Returns: consolidated research report with citations

3. **invoke_ad_generator**: Creates comprehensive ad campaigns with media
   - Use when: After research is complete
   - Parameters: draft_report, target_product, target_audience, campaign_guide_data, trends, creative_brief
   - Returns: ad copy, visual concepts, generated images/videos

Workflow:
1. Check agent health with check_a2a_agents_health() at startup
2. Start with greeting and guide user through PDF upload and trend selection
3. Invoke trends_insights agent for data extraction and trend analysis
4. Invoke research_orchestrator for comprehensive research
5. Invoke ad_generator for creative campaign generation
6. Compile and present final report with all assets

IMPORTANT: Extract the necessary data from responses and maintain in session state.
If an a2a agent is not available, inform the user and suggest running the a2a servers.
"""


# Root agent with a2a client integration
root_agent_a2a_client = Agent(
    model=config.worker_model,
    name="root_agent",
    description="A trend and insight assistant orchestrating multiple a2a server agents via HTTP.",
    instruction=A2A_CLIENT_INSTRUCTION,
    global_instruction=GLOBAL_INSTR,
    tools=[
        trends_tool,
        research_tool,
        ad_tool,
        health_tool,
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