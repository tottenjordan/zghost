N_YOUTUBE_VIDEOS = 3
MAX_YT_DURATION = "7 minutes"
MAX_GOOGLE_SEARCHES_PER_REGION = 3


get_youtube_trends_prompt = """
Follow the steps below to query trending videos from YouTube and prepare them for a marketing analyst to review.

While researching the trends, keep in mind the {campaign_brief}. Use this to find intersectional concepts with the brief.
1) Use the `get_youtube_trends` tool to query the YouTube Data API for trending videos in select target markets.
2) Use the `analyze_youtube_videos` tool to analyze each video. Find each video's URL in the response entry titled: "videoURL".
3) Using the output from the previous step, generate a brief summary describing what is taking place or being discussed. 
4) Use the `query_web` tool to do additional research and confirm findings via google search. Describe the key entities involved. This could be a person, place, organization or named event. This includes their backgrounds, roles, and any other relevant information
5) Describe the relationships between the key entities described in the previous step

When the user is ready, they can transfer the agent back to the parent agent. 
"""

N_YOUTUBE_VIDEOS = 3
MAX_YT_DURATION = "7 minutes"
MAX_GOOGLE_SEARCHES_PER_REGION = 3

trends_generation_instructions = """
Before transferring to any agent, be sure to use the `call_trends_generator_agent` tool to update the list of structured trends to your state.
"""

broad_instructions = f"""
Always cite your sources from the web and Youtube
Limit your google searches to {MAX_GOOGLE_SEARCHES_PER_REGION} per region.
Restrict the number of youtube videos analyzed by {N_YOUTUBE_VIDEOS}
Also make sure that the youtube videos are generally less than {MAX_YT_DURATION}    
"""

trends_generation_prompt = """
Understand the output of the latest trends from this research and produce structured data output using the call_trends_generator_agent tool
Note all outputs from the agent run and run this tool to update the session state with trends.
Note how to fill the fields out:

    trend_title: str -> Come up with a unique title for the trend
    trend_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
    trend_url: str -> Get the url from the `query_youtube_api` tool
    source_text: str -> Get the text from the `query_web` tool or `analyze_youtube_videos` tool
    key_entities: str -> Develop entities from the source to create a graph (see relations)
    key_relationships: str -> Create relationships between the key_entities to create a graph
    key_audiences: str -> Considering the brief, how does this trend intersect with the audience?
    key_product_insights: str -> Considering the brief, how does this trend intersect with the product?
"""

unified_trends_instructions = broad_instructions + trends_generation_instructions + get_youtube_trends_prompt
