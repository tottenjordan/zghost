N_YOUTUBE_VIDEOS = 3
TARGET_YT_DURATION = "5 minutes"
MAX_YT_DURATION = "10 minutes"
MAX_GOOGLE_SEARCHES_PER_REGION = 3

broad_instructions = f"""
Always cite your sources from the web and Youtube.
When following the instructions below be sure to limit the number of youtube videos analyzed to {N_YOUTUBE_VIDEOS}
Also make sure that the youtube videos are generally less than {TARGET_YT_DURATION}. If a video is longer than {MAX_YT_DURATION}, skip it  
Limit your google searches to {MAX_GOOGLE_SEARCHES_PER_REGION} per region.
"""

create_brief_prompt = """
Do research to better understand the marketing campaign brief and target product: {campaign_brief.target_product}

Your goal is to generate structured insights that adhere to {insights}

Follow this flow:
1) Read the sample {campaign_brief}; note the {campaign_brief.campaign_objectives} and {campaign_brief.target_audience}.
2) Use the `query_web` tool to gather market research from Google Search.
3) Think about how this market research relates to topics described in the {campaign_brief}.
4) Using this market research, provide a detailed brief highlighting where the {campaign_brief.target_product} can win in the marketplace. Cite your sources!
5) Use the `call_insights_generation_agent` tool to update the list of structured {insights} in the session state.
6) Pick the top three insights and use the `query_youtube_api` tool to find videos related to these insights. Come up with really good search queries related to the insights.
7) Use the `analyze_youtube_videos` tool to analyze the videos found in the previous step. Note key insights fom your research hat will later be used to refine the campaign brief
8) Use the `call_insights_generation_agent` tool to add key insights from YouTube to the structured {insights} in the session state.

Always cite your sources from the web and Youtube.

For each insight, be sure to use the `call_insights_generation_agent` tool to update the list of structured {insights} in the session state.
Lastly, once the insights are updated, transfer back to the parent agent.
"""

youtube_url_instructions = """
When using the `analyze_youtube_videos` tool be sure to format the url as https://www.youtube.com/watch?v=videoId.
videoId can be found as an output of the `query_youtube_api` tool.
Here is an example path to the videoID: query_youtube_api_response["items"]["id"]["videoId"]
"""

insights_generation_instructions = """
Before transferring to any agent, be sure to use the `call_insights_generation_agent` tool to update the list of structured {insights} in the session state.
"""

insights_generation_prompt = """
Understand the output from the web and youtube research, considering {campaign_brief}
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
