trends_generation_instructions = """
Before transferring to any agent, be sure to use the `call_trends_generator_agent` tool to update the list of structured trends to your state.
"""

get_youtube_trends_prompt = """
Follow the steps below to query trending videos from YouTube and prepare them for a marketing analyst to review.

Be sure to limit the number of videos to max 5 per region to save time on demos and focus on shorter videos for the same reason.

While researching the trends, keep in mind the {campaign_brief}. Use this to find intersectional concepts with the brief.
1) Use the `get_youtube_trends` tool to query the YouTube Data API for trending videos in select target markets.
2) Use the `analyze_youtube_videos` tool to analyze each video. Find each video's URL in the response entry titled: "videoURL".
3) Using the output from the previous step, generate a brief summary describing what is taking place or being discussed. 
4) Use the `query_web` tool to do additional research and confirm findings via google search. Describe the key entities involved. This could be a person, place, organization or named event. This includes their backgrounds, roles, and any other relevant information
5) Describe the relationships between the key entities described in the previous step

When the user is ready, they can transfer the agent back to the parent agent. 
"""

trends_generation_prompt = """
Understand the output of the latest trends from this research and produce structured data output using the call_trends_generator_agent tool
Note all outputs from the agent run and run this tool to update the session state with trends.
"""