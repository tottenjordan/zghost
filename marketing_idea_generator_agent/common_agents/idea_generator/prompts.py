N_YOUTUBE_VIDEOS = 3
MAX_YT_DURATION = "7 minutes"
MAX_GOOGLE_SEARCHES_PER_REGION = 3

insights_generation_instructions = """
Before transferring to any agent, be sure to use the `call_insights_generation_agent` tool to update the list of insights to the agent's state.
Run this tool after every tool response from `query_web` and `analyze_youtube_videos` tools to capture any detailed information
"""

broad_instructions = f"""
Always cite your sources from the web and Youtube.
When following the instructions below be sure to limit the number of youtube videos analyzed by {N_YOUTUBE_VIDEOS}
Also make sure that the youtube videos are generally less than {MAX_YT_DURATION}
Limit your google searches to {MAX_GOOGLE_SEARCHES_PER_REGION} per region.

Note you can transfer to the trends agent if you want to research trends or you can transfer to the image generation agent
Lastly, you can transfer to the brief_data_generation_agent to update the brief in the session state
"""


create_brief_prompt = """
Given the details below, create a marketing campaign brief for the target product launch:
Follow this flow:
1) Read the sample {campaign_brief}.
2) Use the `query_web` tool to gather market research from Google Search. Cite your sources
3) Understand the market research, given the brief
4) Using this market research, provide a detailed brief highlighting where the target product's new features can win in the marketplace
5) Use the `query_youtube_api` tool to find videos related to step 4 or the brief in general
6) Use the `analyze_youtube_videos` tool to analyze the videos found in step 5. Note key insights to refine the campaign brief
Always cite your sources from the web and Youtube
When the user is ready, they can transfer the agent back to the parent agent.
"""

youtube_url_instructions = """
When using the `analyze_youtube_videos` tool be sure to format the url as https://www.youtube.com/watch?v=videoId.
videoId can be found as an output of the `query_youtube_api` tool.
Here is an example path to the videoID: query_youtube_api_response["items"]["id"]["videoId"]
"""

youtube_analysis_prompt = """
Reference the {campaign_brief}.
How do these videos provide additional marketing insights?
"""

# get_youtube_trends_prompt = """
# To search YouTube for trending videos, use the `get_youtube_trends` tool. For each trending video, complete the following steps:
# 1) Use the `analyze_youtube_videos` tool to analyze each video. Find each video's URL in the response entry titled: "videoURL".
# 2) Generate a brief sumamry describing what is taking place or being discussed
# 3) Describe the key entities involved. This could be a person, place, organization or named event. This includes their backgrounds, roles, and any other relevant information
# 4) Describe the relationships between the key entities described in the previous step
# When the user is ready, they can transfer the agent back to the parent agent.
# """

insights_generation_prompt = """
Understand the output from the web and youtube research, considering {campaign_brief}
Use the agent to produce structured output to the insights state.
How to fill the fields out:
    insight_title: str -> Come up with a unique title for the insight
    insight_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
    insight_urls: List[str] -> Get the url from the `query_youtube_api` tool or `query_web` tool
    key_entities: List[str] -> Develop entities from the source to create a graph (see relations)
    key_relationships: List[str] -> Create relationships between the key_entities to create a graph
    key_audiences: List[str] -> Considering the brief, how does this insight intersect with the audience?
    key_product_insights: List[str] -> Considering the brief, how does this insight intersect with the product?
"""
