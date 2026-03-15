from .orchestrator import CampaignOrchestrator
from .flat_agents import research_agent, ad_creative_agent
from .skills.focus_group.agents import focus_group_evaluator_agent
from .shared_libraries import callbacks

root_agent = CampaignOrchestrator(
    name="root_agent",
    description="Deterministic campaign pipeline orchestrator.",
    sub_agents=[
        research_agent,
        ad_creative_agent,
        focus_group_evaluator_agent,
    ],
    before_agent_callback=[
        callbacks._load_session_state,
        callbacks.campaign_callback_function,
    ],
)
