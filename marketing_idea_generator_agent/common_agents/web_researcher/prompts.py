N_YOUTUBE_VIDEOS = 3
TARGET_YT_DURATION = "7 minutes"
MAX_YT_DURATION = "10 minutes"
MAX_GOOGLE_SEARCHES_PER_REGION = 3

broad_instructions = f"""
Use this agent when the user wants to conduct market research to gather insights related to the marketing campaign guide.
When following the instructions below be sure to limit the number of YouTube videos analyzed to {N_YOUTUBE_VIDEOS}
Also make sure that the YouTube videos are generally less than {TARGET_YT_DURATION}. If a video is longer than {MAX_YT_DURATION}, skip it

"""

# Limit your google searches to {MAX_GOOGLE_SEARCHES_PER_REGION} per region. 

search_research_insights_prompt = """
Following the steps below to conduct research and better understand the marketing campaign guide and target product: {campaign_guide.target_product}

Your goal is to generate structured insights that answer questions like:

- What’s relevant, distinctive, or helpful about the {campaign_guide.target_product} or {campaign_guide.brand}?
- Which product features would the target audience best resonate with?
- How could marketers make a culturally relevant advertisement related to product insights

Follow these steps:

1) Read the provided marketing campaign guide:

{campaign_guide} 

2) Note the campaign objectives: {campaign_guide.campaign_objectives}, and the target audience: 

{campaign_guide.target_audience}

3) Use the `query_web` tool to peform a Google Search for insights related to the target product: {campaign_guide.target_product}.
4) Use the `query_youtube_api` tool to find videos related to the target product: {campaign_guide.target_product}, and target audiences
5) Use the `analyze_youtube_videos` tool to understand the videos found in the previous step and note key insights from your research that will later be used to produce a detailed marketing campaign brief

"""

youtube_url_instructions = """
When using the `analyze_youtube_videos` tool be sure to format the url as https://www.youtube.com/watch?v=videoId.
videoId can be found as an output of the `query_youtube_api` tool.
Here is an example path to the videoID: query_youtube_api_response["items"]["id"]["videoId"]
"""

insights_generation_instructions = """
Before transferring to any agent, be sure to use the `call_insights_generation_agent` tool to update the list of structured `insights` in the session state.
Lastly, once the insights are updated, you can transfer back to the parent agent.
"""

insights_generation_prompt = """
Understand the output from the web and YouTube research, considering the marketing campaign guide:

{campaign_guide}

Use the agent to produce structured output to the insights state.
How to fill the fields out:
    insight_title: str -> Come up with a unique title for the insight
    insight_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
    insight_urls: str -> Get the url from the `query_youtube_api` tool or `query_web` tool
    key_entities: str -> Develop entities from the source to create a graph (see relations)
    key_relationships: str -> Create relationships between the key_entities to create a graph
    key_audiences: str -> Considering the guide, how does this insight intersect with the audience?
    key_product_insights: str -> Considering the guide, how does this insight intersect with the product?
Be sure to consider any existing {insights} but **do not output any insights** that are already on this list.
Also, consider the intersectionality of the intersections of the Product: {campaign_guide.target_product}, along with {campaign_guide.target_audience}.
Utilize any existing {trends} and understand where there are any relevant intersections to the goals of the campaign.
"""


unified_insights_prompt = (
    broad_instructions
    + search_research_insights_prompt
    + youtube_url_instructions
    + insights_generation_instructions
)
