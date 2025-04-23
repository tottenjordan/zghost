get_youtube_trends_prompt = """
Follow the steps below to query trending videos from YouTube and prepare them for a marketing analyst to review.

Be sure to limit the number of videos to max 2 per region to save time on demos and focus on shorter videos for the same reason.
Make sure the video is less than 2 minutes long.
While researching the trends, keep in mind the {marketing_brief}. Use this to find intersectional concepts with the brief.
1) Use the `get_youtube_trends` tool to query the YouTube Data API for trending videos in select target markets.
2) Use the `analyze_youtube_videos` tool to analyze each video. Find each video's URL in the response entry titled: "videoURL".
3) Generate a brief summary describing what is taking place or being discussed, use the `analyze_youtube_videos` to analyze the video with Gemini
4) Use the `query_web` tool to do additional research and confirm findings via google search
5) Describe the key entities involved. This could be a person, place, organization or named event. This includes their backgrounds, roles, and any other relevant information
6) Describe the relationships between the key entities described in the previous step
When the user is ready, they can transfer the agent back to the parent agent. 
"""