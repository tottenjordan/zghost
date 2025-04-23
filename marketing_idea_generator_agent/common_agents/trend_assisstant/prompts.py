get_youtube_trends_prompt = """
Follow the steps below to query trending videos from YouTube and prepare them for a marketing analyst to review.

1) Use the `get_youtube_trends` tool to query the YouTube Data API for trending videos in select target markets.
1) Use the `analyze_youtube_videos` tool to analyze each video. Find each video's URL in the response entry titled: "videoURL".
2) Generate a brief sumamry describing what is taking place or being discussed
3) Describe the key entities involved. This could be a person, place, organization or named event. This includes their backgrounds, roles, and any other relevant information
4) Describe the relationships between the key entities described in the previous step
When the user is ready, they can transfer the agent back to the parent agent. 
"""