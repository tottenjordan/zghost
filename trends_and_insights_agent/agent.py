import datetime

from google.genai import types
from google.adk.agents import Agent

from .orchestrator import (
    ORCHESTRATOR_INSTRUCTION,
    gather_trends,
    select_trend,
    run_research,
    run_ad_creative,
    generate_images,
    generate_commercial,
    run_focus_group,
    save_report,
)
from .shared_libraries.config import config
from .shared_libraries import callbacks

root_agent = Agent(
    name="root_agent",
    model=config.worker_model,
    description="Marketing campaign pipeline orchestrator. Runs trends, research, creative, image gen, video, focus group, and report stages.",
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        gather_trends,
        select_trend,
        run_research,
        run_ad_creative,
        generate_images,
        generate_commercial,
        run_focus_group,
        save_report,
    ],
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=8192),
    ),
    before_agent_callback=[
        callbacks._load_session_state,
        callbacks.campaign_callback_function,
    ],
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
)
