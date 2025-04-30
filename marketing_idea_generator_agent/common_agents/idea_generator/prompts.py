N_YOUTUBE_VIDEOS = 3
TARGET_YT_DURATION = "7 minutes"
MAX_YT_DURATION = "10 minutes"
MAX_GOOGLE_SEARCHES_PER_REGION = 3

broad_instructions = f"""
Use this agent when the user wants to conduct market research for insights related to the campaign brief.
When following the instructions below be sure to limit the number of YouTube videos analyzed to {N_YOUTUBE_VIDEOS}
Also make sure that the YouTube videos are generally less than {TARGET_YT_DURATION}. If a video is longer than {MAX_YT_DURATION}, skip it  
"""

create_brief_prompt = """
Conduct research to better understand the marketing campaign brief and target product: {campaign_brief.target_product}

Your goal is to generate structured insights to populate {insights}

Follow this flow:
1) Read the provided {campaign_brief}
2) Use the `query_youtube_api` tool to find videos related to the {campaign_brief.target_product} and {campaign_brief.target_audience}
3) Use the `analyze_youtube_videos` tool to understand the videos found in the previous step. Note key insights from your research that will later be used to refine the campaign brief
4) Use the `call_insights_generation_agent` tool to add each insight to the structured {insights} in the session state.

Always cite your sources from YouTube.
"""

youtube_url_instructions = """
When using the `analyze_youtube_videos` tool be sure to format the url as https://www.youtube.com/watch?v=videoId.
videoId can be found as an output of the `query_youtube_api` tool.
Here is an example path to the videoID: query_youtube_api_response["items"]["id"]["videoId"]
"""

insights_generation_instructions = """
Before transferring to any agent, be sure to use the `call_insights_generation_agent` tool to update the list of structured {insights} in the session state.
Lastly, once the insights are updated, you can transfer back to the parent agent.
"""

insights_generation_prompt = """
Understand the output from the web and YouTube research, considering {campaign_brief}
Use the agent to produce structured output to the insights state.
How to fill the fields out:
    insight_title: str -> Come up with a unique title for the insight
    insight_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
    insight_urls: str -> Get the url from the `query_youtube_api` tool or `query_web` tool
    key_entities: str -> Develop entities from the source to create a graph (see relations)
    key_relationships: str -> Create relationships between the key_entities to create a graph
    key_audiences: str -> Considering the brief, how does this insight intersect with the audience?
    key_product_insights: str -> Considering the brief, how does this insight intersect with the product?
"""


unified_insights_prompt = (
    broad_instructions
    + create_brief_prompt
    + youtube_url_instructions
    + insights_generation_instructions
)
