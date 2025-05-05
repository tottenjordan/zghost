N_YOUTUBE_TREND_VIDEOS = 15
TARGET_YT_DURATION = "5 minutes"
MAX_YT_DURATION = "10 minutes"

broad_instructions = f"""
Use this agent when the user wants to find trending content on YouTube.
When you display trending videos to the user. Be sure to display the top {N_YOUTUBE_TREND_VIDEOS} trending videos from YouTube.
"""

get_youtube_trends_prompt = """
Follow the steps below to understand key themes from trending content on YouTube. 
Remember: these themes don't have to be directly related to {campaign_guide.target_product}. We just want the themes for future brainstorming exercises.

1) Use the `get_youtube_trends` tool to query the YouTube Data API for the top trending videos in each target market. Start with "Shorts" and expand to longer videos if necessary. Display each video's title, duration, and URL for the user.
2) Ask the user which trending video(s) to proceed with.
3) For each user-selected video from step two, fin the video's URL in the response entry titled: "videoURL". Use the `analyze_youtube_videos` tool to analyze each video and understand what is being discussed.
4) Using the output from the previous step, generate a concise summary describing what is taking place or being discussed. Be sure to explain if you think this trend will resonate with the {campaign_guide.target_audience}.
5) For each trending video, suggest how it could possibly relate to the {campaign_guide.target_product} in a marketing campaign. Use the `call_trends_generator_agent` tool to add these trends from YouTube to the structured `trends` in the session state.

Then prompt the user on what to do next. 
"""
# Lastly, after calling the `call_trends_generator_agent` tool, transfer back to the parent agent


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
    key_audiences: str -> Considering the guide, how does this trend intersect with the audience?
    key_product_insights: str -> Considering the guide, how does this trend intersect with the product?

Be sure to consider any existing {trends} but **do not output any insights** that are already on this list.
Also, consider the intersectionality of the intersections of the Product: {campaign_guide.target_product}, along with {campaign_guide.target_audience}.
Utilize any existing {insights} and understand where there are any relevant intersections to the goals of the campaign.
"""

unified_trends_instructions = broad_instructions + get_youtube_trends_prompt
