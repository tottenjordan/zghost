# from google.genai import types
from google.adk.agents import SequentialAgent

from .sub_agents.campaign_insights_researcher.agent import campaign_insights_researcher
from .sub_agents.yt_trends_researcher.agent import yt_trends_researcher
from .sub_agents.gs_trends_researcher.agent import gs_trends_researcher


# ========================
# sequential researchers
# ========================

web_researcher_agent = SequentialAgent(
    name="web_researcher_agent",
    sub_agents=[
        campaign_insights_researcher,
        yt_trends_researcher,
        gs_trends_researcher,
    ],
    description="Coordinates web research by executing the following sub-agents sequentially: `campaign_insights_researcher`, `yt_trends_researcher`, `gs_trends_researcher`",
)


# ========================
# prompt-driven researchers
# ========================
# tools = [
#     query_web,
#     query_youtube_api,
#     LongRunningFunctionTool(analyze_youtube_videos),
#     call_insights_generation_agent,
#     call_yt_trends_generator_agent,
#     call_search_trends_generator_agent,
# ]
# web_researcher_agent = Agent(
#     model=MODEL,
#     name="web_researcher_agent",
#     instruction=AUTO_UNIFIED_RESEARCH_PROMPT,  # unified_web_research_prompt,
#     tools=tools,
#     generate_content_config=types.GenerateContentConfig(
#         temperature=1.0,
#     ),
# )
