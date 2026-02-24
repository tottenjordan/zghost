from google.genai import types
from google.adk.agents import Agent

from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from .tools import analyze_commercial_video, save_focus_group_evaluation
from .prompts import FOCUS_GROUP_INSTR

focus_group_evaluator_agent = Agent(
    model=config.critic_model,
    name="focus_group_evaluator_agent",
    description=(
        "Analyzes a 30-second commercial video with Gemini vision and "
        "simulates a focus group reviewing it for quality, consistency, "
        "trend relevance, and audience uplift potential. Saves a GO/NO-GO "
        "recommendation to session state."
    ),
    instruction=FOCUS_GROUP_INSTR,
    tools=[analyze_commercial_video, save_focus_group_evaluation],
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    before_model_callback=callbacks.rate_limit_callback,
)
