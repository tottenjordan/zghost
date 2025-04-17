create_brief_prompt = """
Given the details below, create a marketing campaign brief for the target product launch:
Follow this flow:
1) Read the sample {campaign_brief}.
2) Use the `query_web` tool to gather market research from Google Search
3) Understand the market research, given the brief
4) Using this market research, provide a detailed brief highlighting where the target product's new features can win in the marketplace
5) Use the `query_youtube_api` tool to find videos related to the campaign brief
6) Use the `analyze_youtube_videos` tool to analyze the videos found in step 5. Note key insights to refine the campaign brief
7) Create a set of descriptions and prompts that can be used downstream to generate video and image assets for the campaign
Always cite your sources from the tools.
Be sure to reference the {campaign_brief}
When the user is ready, they can transfer the agent back to the parent agent, or to the image generation agent for image or video generation tasks.
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

trends_analysis_prompt = "TODO"