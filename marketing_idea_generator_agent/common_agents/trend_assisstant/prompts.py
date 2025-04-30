N_YOUTUBE_VIDEOS = 3
TARGET_YT_DURATION = "5 minutes"
MAX_YT_DURATION = "10 minutes"
MAX_GOOGLE_SEARCHES_PER_REGION = 3

broad_instructions = f"""
Use this agent to conduct web research via Google and YouTube. 
Limit your google searches to {MAX_GOOGLE_SEARCHES_PER_REGION} per region.
Restrict the number of youtube videos analyzed by {N_YOUTUBE_VIDEOS}
Also make sure that the youtube videos are generally less than {TARGET_YT_DURATION}. If a video is longer than {MAX_YT_DURATION}, skip it
Always cite your sources from the web and Youtube
"""

get_youtube_trends_prompt = """
Follow the steps below to understand key themes from trending content on YouTube. 
These themes don't have to be directly related to {campaign_brief.target_product}. We just want the themes for future brainstorming exercises.

1) Use the `get_youtube_trends` tool to query the YouTube Data API for trending videos in each target market.
2) Use the `analyze_youtube_videos` tool to analyze each video. Find each video's URL in the response entry titled: "videoURL".
3) Using the output from the previous step, generate a concise summary describing what is taking place or being discussed. 
4) For each trending video, provide insights into how it could possibly relate to the {campaign_brief.target_product}
5) Use the `call_trends_generator_agent` tool to add any trends from YouTube to the structured {trends} in the session state.

Lastly, after calling the `call_trends_generator_agent` tool, transfer back to the parent agent
"""

trends_generation_instructions = """
Before transferring to any agent, be sure to use the `call_trends_generator_agent` tool to update the list of structured {trends} to your state.
"""

trends_generation_prompt = """
Understand the output of the latest trends from this research and produce structured data output using the `call_trends_generator_agent` tool
Note all outputs from the agent run and run this tool to update the session state with trends.
Note how to fill the fields out:

    trend_title: str -> Come up with a unique title for the trend
    trend_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
    trend_urls: str -> Get the url from the `query_youtube_api` tool
    source_texts: str -> Get the text from the `query_web` tool or `analyze_youtube_videos` tool
    key_entities: str -> Develop entities from the source to create a graph (see relations)
    key_relationships: str -> Create relationships between the key_entities to create a graph
    key_audiences: str -> Considering the brief, how does this trend intersect with the audience?
    key_product_insights: str -> Considering the brief, how does this trend intersect with the product?
"""

unified_trends_instructions = (
    broad_instructions + get_youtube_trends_prompt + trends_generation_instructions
)
