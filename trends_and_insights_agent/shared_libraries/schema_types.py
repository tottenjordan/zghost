"""Common data schema and types for the Trends & Insights Agent"""

from typing import Optional, Union

from google.genai import types
from pydantic import BaseModel, Field


# Convenient declaration for controlled generation.
json_response_config = types.GenerateContentConfig(
    response_mime_type="application/json"
)


# =============================
# Research Structured Feedback
# =============================
class CampaignSearchQuery(BaseModel):
    """Model representing a specific search query for web search."""

    search_query: str = Field(
        description="A highly specific and targeted query for web search."
    )


class CampaignFeedback(BaseModel):
    """Model for providing evaluation feedback on research quality."""

    comment: str = Field(
        description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the research."
    )
    follow_up_queries: list[CampaignSearchQuery] | None = Field(
        default=None,
        description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if no follow-up questions needed.",
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
    target_audience: list[str] = Field(
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
    # key_insights: list[str] = Field(  # TODO: fix
    #     description="Referencable data points that show intersection between goals and broad information sources"
    # )
    key_selling_points: list[str] = Field(
        description="Aspects of the `target_product` that distinguish it from competitors and persuades customers to choose it"
    )


# ========================
# Insight Generation
# ========================
class Insight(BaseModel):
    "Data model for insights from Google and YouTube research."

    insight_title: str = Field(
        description="Come up with a unique title for the insight."
    )
    insight_text: str = Field(
        description="Generate a summary of the insight from the web research."
    )
    insight_urls: list[str] = Field(
        description="Get the url(s) used to generate the insight."
    )
    key_entities: list[str] = Field(
        description="Extract any key entities discussed in the gathered context."
    )
    key_relationships: list[str] = Field(
        description="Describe the relationships between the Key Entities you have identified."
    )
    key_audiences: str = Field(
        description="Considering the guide, how does this insight intersect with the audience?"
    )
    key_product_insights: str = Field(
        description="Referencable data points that show intersection between campaign goals, target product, target audience, and web research."
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
    trend_urls: list[str] = Field(description="url for the trending video")
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
    key_relationships: list[str] = Field(
        description="Relationships between the Key Entities, especially as they relate to the `search_trend`."
    )
    key_audiences: list[str] = Field(
        description="Ideas or angles for helping this trend resonate with the target audience described in the `campaign_guide`."
    )
    key_product_insights: list[str] = Field(
        description="Suggestions for finding the intersection of this `search_trend` with the target product."
    )


class Search_Trends(BaseModel):
    "Data model for many trending topics gathered from Google Search."

    search_trends: list[Search_Trend]
