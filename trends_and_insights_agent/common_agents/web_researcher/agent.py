from google.genai import types
from google.adk.agents import Agent, ParallelAgent
from google.adk.tools import LongRunningFunctionTool

# from google.adk.tools import google_search

from ...prompts import global_instructions
from ...utils import MODEL
from ...tools import (
    query_web,
    query_youtube_api,
    analyze_youtube_videos,
    call_insights_generation_agent,
    call_yt_trends_generator_agent,
    call_search_trends_generator_agent,
)
from .prompts import (
    AUTO_UNIFIED_RESEARCH_PROMPT,
    web_efficiency_guidance,
)


# ========================
# parallel researchers
# ========================

# You have access to the following tools only:
# *   `query_web` : Use this tool to perform web searches with Google Search.
# *   `query_youtube_api` : Use this tool to find videos related to specific criteria.
# *   `analyze_youtube_videos` : Use this tool to process and 'understand' YouTube videos.
# *   `call_insights_generation_agent` : Use this tool to update the `insights` session state from the results of your web research.

# Researcher 1: campaign insights
_PAR_INSIGHT_PROMPT = """
You are a Research Assistant specializing in marketing campaign insights.

Your goal is to conduct web research and gather insights related to concepts from the campaign guide. These insights should answer questions like:
    - What's relevant, distinctive, or helpful about the {campaign_guide.target_product} or {campaign_guide.brand}?
    - Which product features would the target audience best resonate with?
    - How could marketers make a culturally relevant advertisement related to product insights?

Follow these steps to conduct research and generate insights:
    1)   Use the `query_web` tool to perform a Google Search and gather insights on several topics described in the campaign guide.
    2)   Use the `query_youtube_api` tool to find videos related to the target product and target audiences.
    3)   Use the `analyze_youtube_videos` tool to understand the videos found in the previous step and note key insights from your research. 
    4)   Use the `call_insights_generation_agent` tool to update the list of structured `insights` in the session state.

"""
researcher_agent_1 = Agent(
    name="CampaignInsightsResearcher",
    model=MODEL,
    instruction=web_efficiency_guidance + _PAR_INSIGHT_PROMPT,
    description="Researches topics listed in the campaign_guide e.g., target product, target audience, etc.",
    tools=[
        query_web,
        query_youtube_api,
        LongRunningFunctionTool(analyze_youtube_videos),
        call_insights_generation_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)

# Conduct research to better understand the context of trending YouTube videos (e.g., `target_yt_trends`).
# better understand the context of the trending video(s), including any key themes that would resonate with our target audiences:
# You have access to the following tools only:
# *   `query_web` : Use this tool to perform web searches with Google Search.
# *   `analyze_youtube_videos` : Use this tool to process and 'understand' YouTube videos.
# *   `call_yt_trends_generator_agent` : Use this tool to update the `yt_trends` session state from your analysis of trending videos.

# Researcher 2: trending YouTube
_PAR_YT_TREND_PROMPT = """
You are a Research Assistant specializing in YouTube trends.

Your goal is to conduct web research to gather insights related to the trending YouTube video(s). These insights should answer questions like:
    - What is the video about? what is being discussed? Who is involved?
    - Why is this video trending? Are there any themes that would resonate with our target audience(s)?
    - Is there any opportunity to connect this trend to our campaign guide?

Follow these steps to conduct research and generate insights:
    1)   For each entry in the `target_yt_trends` session state, use the `analyze_youtube_videos` tool to analyze the `video_url`.
    2)   To better understand key concepts and entities mentioned in the video, use the `query_web` tool to perform Google Searches about them.
    3)   Generate a concise summary describing the context of the video. For example, what is taking place? Why is it trending? Be sure to explain if you think this trend will resonate with the target_audience described in the `campaign_guide`.
    4)   Use the `call_yt_trends_generator_agent` tool to store the trend summary and context in the `yt_trends` session state.

"""
researcher_agent_2 = Agent(
    name="YT_TrendsResearcher",
    model=MODEL,
    instruction=web_efficiency_guidance + _PAR_YT_TREND_PROMPT,
    description="Researches trending YouTube videos selected by the user.",
    tools=[
        query_web,
        LongRunningFunctionTool(analyze_youtube_videos),
        call_yt_trends_generator_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)

# You have access to the following tools only:
# *   `query_web` : Use this tool to perform web searches with Google Search.
# *   `call_search_trends_generator_agent` : Use this tool to update the `search_trends` session state from your web research on trending search topics.

# Researcher 3: trending Search
_PAR_GS_TREND_PROMPT = """
You are a Research Assistant specializing in Search trends.

Your goal is to conduct targeted research to better understand the cultural significance of the trending Search terms. Your research should answer questions like:
    - Why are these search terms trending? Who is involved?
    - Are there any related themes that would resonate with our target audience(s)?
    - Is there any opportunity to connect this trend to our campaign guide?

Follow these steps to conduct research and generate insights:
    1)   For each entry in `target_search_trends`, use the `query_web` tool to perform several Google Searches related to the trend topic and concepts from the `campaign_guide`.
    2)   Using the output from the previous step, generate trend context that includes a concise summary describing what is taking place or being discussed:
            a. Describe any key entities (i.e., people, places, organizations, named events, etc.).
            b. Describe the relationships between these key entities, especially in the context of the trending topic.
            c. Explain if you think this trend will resonate with the `target_audience` described in the `campaign_guide`.
            d. Suggest how this trending content could possibly relate to the {campaign_guide.target_product} in a marketing campaign. 
    3)   Use the `call_search_trends_generator_agent` tool to store this trend context in the `search_trends` session state.

"""
researcher_agent_3 = Agent(
    name="GS_TrendsResearcher",
    model=MODEL,
    instruction=web_efficiency_guidance + _PAR_GS_TREND_PROMPT,
    description="Researches trending Search terms selected by the user.",
    tools=[
        query_web,
        call_search_trends_generator_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)

# --- 2. Create the ParallelAgent (Runs researchers concurrently) ---
# This agent orchestrates the concurrent execution of the researchers.
# It finishes once all researchers have completed and stored their results in state.
parallel_research_agent = ParallelAgent(
    name="ParallelWebResearchAgent",
    sub_agents=[researcher_agent_1, researcher_agent_2, researcher_agent_3],
    description="Runs multiple research agents in parallel to gather information. When finished, transfer back to the root agent.",
)

web_researcher_agent = parallel_research_agent


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
