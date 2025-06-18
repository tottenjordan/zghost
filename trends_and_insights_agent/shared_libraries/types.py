"""Common data schema and types for the Trends & Insights Agent"""

from typing import Optional, Union

from google.genai import types
from pydantic import BaseModel, Field


# Convenient declaration for controlled generation.
json_response_config = types.GenerateContentConfig(
    response_mime_type="application/json"
)


# ==========================
# Marketing Guide Data Gen
# ==========================
# used by `campaign_guide_data_generation_agent``
class MarketingCampaignGuide(BaseModel):
    "Data model for the marketing campaign guide."

    campaign_name: str = Field(
        description="given name of campaign; could be title of uploaded `campaign_guide`"
    )
    brand: str = Field(description="target product's brand")
    target_product: str = Field(
        description="the subject of the marketing campaign objectives"
    )
    target_audience: str = Field(
        description="specific group(s) we intended to reach. Typically described with demographic, psychographic, and behavioral profile of the ideal customer or user"
    )
    target_regions: list[str] = Field(
        description="specific cities and/or countries we intend to reach"
    )
    campaign_objectives: list[str] = Field(
        description="goals that define what we plan to achieve"
    )
    media_strategy: list[str] = Field(
        description="media channels or formats we intend to use to reach our audiences"
    )
    key_insights: list[str] = Field(  # TODO: fix
        description="referencable data points that shows intersection between goals and broad information sources"
    )
    campaign_highlights: list[str] = Field(
        description="aspects of product, brand, event, etc. we wish to highlight e.g., key selling points or competitive advantages of the target product"
    )


# ========================
# Insight Generation
# ========================
class Insight(BaseModel):
    "Data model for insights from Google and YouTube research."

    insight_title: str = Field(description="a unique title for the insight")
    insight_text: str = Field(
        description="text from the `analyze_youtube_videos` tool or `query_web` tool"
    )
    insight_urls: list[str] = Field(
        description="the url from the `query_youtube_api` tool or `query_web` tool"
    )
    key_entities: str = Field(
        description="entities from the source to create a graph (see relations)"
    )
    key_relationships: list[str] = Field(
        description="relationships between the key_entities to create a graph"
    )
    key_audiences: str = Field(
        description="ideas for intersecting this insight with the target audience"
    )
    key_product_insights: str = Field(
        description="ideas for intersecting this insight with the target product"
    )


class Insights(BaseModel):
    "Data model for insights from Google and YouTube research."

    insights: list[Insight]


# ==========================
# YouTube Trends
# ==========================


class YT_Trend(BaseModel):
    "Data model for trending content on YouTube."

    # trend_title: str = Field(description="a unique title for the trend")
    video_title: str = Field(description="exact name of the trending YouTube video")
    trend_text: str = Field(
        description="source text from video or URL analysis e.g., output from the `analyze_youtube_videos` or `query_web` tools"
    )
    trend_urls: str = Field(description="url for the trending video")
    key_entities: list[str] = Field(description="Key Entities discussed in the video")
    key_relationships: list[str] = Field(
        description="the relationships between any Key Entities"
    )
    key_audiences: list[str] = Field(
        description="ideas for relating this trend to the target audiences described in the `campaign_guide`"
    )
    key_product_insights: list[str] = Field(
        description="a few insights from the intersection of the trending content and the target product."
    )


class YT_Trends(BaseModel):
    "Data model for all trending content gathered from YouTube."

    yt_trends: list[YT_Trend]


# ==============================
# Google Search Trends
# ==============================


class Search_Trend(BaseModel):
    "Data model for a trending topic from Google Search."

    trend_title: str = Field(
        description="The user-selected topic from Google Search Trends. Should be the exact words as seen in the source data."
    )
    trend_text: str = Field(
        description="Source text from the URL(s) providing context on the `search_trend`."
    )
    trend_urls: list[str] = Field(
        description="Any url(s) that provided reliable context for the `search_trend`."
    )
    key_entities: list[str] = Field(
        description="Any Key Entities discussed in the gathered context."
    )
    key_relationships: str = Field(
        description="Relationships between the Key Entities, especially as they relate to the `search_trend`."
    )
    key_audiences: list[str] = Field(
        description="Ideas or angles for helping this trend resonate with the target audience described in the `campaign_guide`."
    )
    key_product_insights: list[str] = Field(
        description="Suggestions for finding the intersection og this `search_trend` with the target product."
    )


class Search_Trends(BaseModel):
    "Data model for many trending topics gathered from Google Search."

    search_trends: list[Search_Trend]
