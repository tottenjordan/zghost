# imports
import os
from pydantic import BaseModel
from google.adk.agents import Agent
from google.genai import types
from .prompts import trends_generation_prompt
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

import googleapiclient.discovery
from google.cloud import secretmanager as sm


# clients
sm_client = sm.SecretManagerServiceClient()
SECRET_ID = (
    f'projects/{os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER")}/secrets/yt-data-api'
)
SECRET_VERSION = "{}/versions/1".format(SECRET_ID)
response = sm_client.access_secret_version(request={"name": SECRET_VERSION})
YOUTUBE_DATA_API_KEY = response.payload.data.decode("UTF-8")
youtube_client = googleapiclient.discovery.build(
    serviceName="youtube", version="v3", developerKey=YOUTUBE_DATA_API_KEY
)


# Trends Structured Tool
class Trend(BaseModel):
    "Data model for trends from Google and Youtube research."

    trend_title: str
    trend_text: str
    trend_urls: str
    key_entities: str
    key_relationships: str
    key_audiences: str
    key_product_insights: str


class Trends(BaseModel):
    "Data model for trends from Google and Youtube research."

    trends: list[Trend]


# agent tool to capture trends
trends_generator_agent = Agent(
    model="gemini-2.0-flash-001",
    name="trends_generator_agent",
    instruction=trends_generation_prompt,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    output_schema=Trends,
    output_key="trends",
)


async def call_trends_generator_agent(question: str, tool_context: ToolContext):
    """
    Tool to call the insights generation agent.
    Question: The question to ask the agent, use the tool_context to extract the following schema:
        trend_title: str -> Come up with a unique title for the trend
        trend_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
        trend_urls: str -> Get the url from the `query_youtube_api` tool
        source_texts: str -> Get the text from the `query_web` tool or `analyze_youtube_videos` tool
        key_entities: str -> Develop entities from the source to create a graph (see relations)
        key_relationships: str -> Create relationships between the key_entities to create a graph
        key_audiences: str -> Considering the brief, how does this trend intersect with the audience?
        key_product_insights: str -> Considering the brief, how does this trend intersect with the product?
    tool_context: The tool context.
    """

    agent_tool = AgentTool(trends_generator_agent)
    existing_trends = tool_context.state.get("trends")

    trends = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    if existing_trends is not []:
        trends["trends"].extend(
            existing_trends
        )  # TODO: Validate how to keep a history of trends & insights
    tool_context.state["trends"] = trends["trends"]
    return {"status": "ok"}


def get_youtube_trends(
    region_code: str,
    max_results: int = 5,
) -> dict:
    """
    Returns a dictionary of videos that match the API request parameters e.g., trending videos

    Args:
        region_code (str): selects a video chart available in the specified region. Values are ISO 3166-1 alpha-2 country codes.
            For example, the region_code for the United Kingdom would be 'GB', whereas 'US' would represent The United States.
        max_results (int): The number of video results to return.

    Returns:
        dict: The response from the YouTube Data API.
    """

    request = youtube_client.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    )
    trend_response = request.execute()
    return trend_response


## TODO: create tool for gathering Search trends from BigQuery public dataset
# def get_search_trends(
#     region_code: str = "US",
#     max_results: int = 7,
#     # youtube_client: googleapiclient.discovery.Resource = youtube_client,
# ) -> dict:


# Set up Integration Connectors
# https://cloud.google.com/integration-connectors/docs/setup-integration-connectors

# bigquery_toolset = ApplicationIntegrationToolset(
#     project="your-gcp-project-id",
#     location="your-gcp-project-location",
#     connection="your-connection-name",
#     entity_operations=["table_name": ["LIST"]],
# )

# agent = LlmAgent(
#   ...
#   tools = bigquery_toolset.get_tools()
# )
