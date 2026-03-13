from .orchestrator import CampaignOrchestrator

from .common_agents.trend_assistant.agent import trends_and_insights_agent
from .common_agents.staged_researcher.agent import research_orchestrator
from .common_agents.ad_content_generator.creative_orchestrator import (
    CreativeProductionOrchestrator,
    commercial_qa_agent,
)
from .common_agents.ad_content_generator.agent import ad_content_generator_agent
from .skills.av_studio.agents import av_editing_studio_agent
from .skills.focus_group.agents import focus_group_evaluator_agent

from .shared_libraries import callbacks

# Build the creative production orchestrator (ad creative + AV studio + QA)
creative_production_orchestrator = CreativeProductionOrchestrator(
    name="creative_production_orchestrator",
    description="Orchestrate creative production: ad copy, visual generation, commercial production, and quality evaluation.",
    sub_agents=[
        ad_content_generator_agent,
        av_editing_studio_agent,
        commercial_qa_agent,
    ],
    after_agent_callback=[
        callbacks.save_creative_skill_to_memory,
        callbacks.after_agent_skill_reflection,
    ],
)

root_agent = CampaignOrchestrator(
    name="root_agent",
    description="Deterministic campaign pipeline orchestrator.",
    sub_agents=[
        trends_and_insights_agent,
        research_orchestrator,
        creative_production_orchestrator,
        focus_group_evaluator_agent,
    ],
    before_agent_callback=[
        callbacks._load_session_state,
        callbacks.campaign_callback_function,
    ],
)
