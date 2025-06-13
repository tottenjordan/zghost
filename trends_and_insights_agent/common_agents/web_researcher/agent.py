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
from .prompts import AUTO_UNIFIED_RESEARCH_PROMPT  # , unified_web_research_prompt


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


# ========================
# paralell researchers
# ========================

# Researcher 1: campaign insights
_PAR_INSIGHT_PROMPT = """
 You are a Research assistant specializing in marketing campaign insights.

You have access to the following tools only:
*   `query_web` : Use this tool to perform web searches with Google Search.
*   `query_youtube_api` : Use this tool to find videos related to specific criteria.
*   `analyze_youtube_videos` : Use this tool to process and 'understand' YouTube videos.
*   `call_insights_generation_agent` : Use this tool to update the `insights` session state from the results of your web research.

Your goal is to **generate structured `insights`** that help marketers create relevant campaigns. These insights should answer questions like:
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
    instruction=_PAR_INSIGHT_PROMPT,
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


# Researcher 2: trending YouTube
_PAR_YT_TREND_PROMPT = """
You are a Research assistant specializing in YouTube trends.
Conduct research to better understand the context of trending YouTube videos (e.g., `target_yt_trends`).

You have access to the following tools only:
*   `query_web` : Use this tool to perform web searches with Google Search.
*   `analyze_youtube_videos` : Use this tool to process and 'understand' YouTube videos.
*   `call_yt_trends_generator_agent` : Use this tool to update the `yt_trends` session state from your analysis of trending videos.

Your goal is to understand key themes from the video content:
    1)   Read populated entries from the `target_yt_trends` session state. For each entry, use the `analyze_youtube_videos` tool to analyze the `video_url`.
    2)   To better understand key concepts or entities mentioned in the video, use the `query_web` tool to perform several Google Searches about them.
    3)   Generate trend context that includes a concise summary describing what is taking place or being discussed in the video. Be sure to explain if you think this trend will resonate with the target_audience described in the `campaign_guide`.
    4)   Use the `call_yt_trends_generator_agent` tool to store this trend context in the `yt_trends` session state.

"""
researcher_agent_2 = Agent(
    name="YT_TrendsResearcher",
    model=MODEL,
    instruction=_PAR_YT_TREND_PROMPT,
    tools=[
        query_web,
        LongRunningFunctionTool(analyze_youtube_videos),
        call_yt_trends_generator_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)


# Researcher 3: trending Search
_PAR_GS_TREND_PROMPT = """
You are a Research assistant specializing in YouTube trends.
Conduct targeted research to better understand the context of trending topics (e.g., `target_search_trends`) from Google Search.

You have access to the following tools only:
*   `query_web` : Use this tool to perform web searches with Google Search.
*   `call_search_trends_generator_agent` : Use this tool to update the `search_trends` session state from your web research on trending search topics.

Your goal is to understand the cultural significance of the trending Search topics/terms:
    1)   Read populated entries from `target_search_trends`. For each entry, use the `query_web` tool to perform several Google Searches related to the trend topic and concepts from the `campaign_guide`.
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
    instruction=_PAR_GS_TREND_PROMPT,
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
