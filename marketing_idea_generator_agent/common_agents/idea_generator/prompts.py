create_brief_prompt = """
Given the details below, create a marketing campaign brief for the target product launch:
Follow this flow:
1) Read the sample {campaign_brief}.
2) Use the `query_web` tool to gather market research from Google Search. Cite your sources
3) Understand the market research, given the brief
4) Using this market research, provide a detailed brief highlighting where the target product's new features can win in the marketplace
5) Use the `query_youtube_api` tool to find videos related to step 4
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