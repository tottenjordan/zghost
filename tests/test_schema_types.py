"""Unit tests for schema_types.py - Pydantic models validation."""

import pytest
from pydantic import ValidationError

from trends_and_insights_agent.shared_libraries.schema_types import (
    CampaignSearchQuery,
    CampaignFeedback,
    MarketingCampaignGuide,
    Insight,
    Insights,
    YT_Trend,
    YT_Trends,
    Search_Trend,
    Search_Trends,
)


class TestCampaignSearchQuery:
    """Tests for CampaignSearchQuery schema."""

    def test_valid_search_query(self):
        """Test that CampaignSearchQuery can be instantiated with valid data."""
        query = CampaignSearchQuery(search_query="Nike running shoes trends 2026")
        assert query.search_query == "Nike running shoes trends 2026"

    def test_empty_search_query(self):
        """Test that empty string is accepted (no field validation)."""
        query = CampaignSearchQuery(search_query="")
        assert query.search_query == ""

    def test_missing_field_raises_error(self):
        """Test that missing required field raises ValidationError."""
        with pytest.raises(ValidationError):
            CampaignSearchQuery()


class TestCampaignFeedback:
    """Tests for CampaignFeedback schema."""

    def test_valid_feedback_with_queries(self):
        """Test CampaignFeedback with follow-up queries."""
        feedback = CampaignFeedback(
            comment="Research is missing data on target demographics",
            follow_up_queries=[
                CampaignSearchQuery(search_query="Gen Z shopping behavior 2026"),
                CampaignSearchQuery(search_query="TikTok marketing trends"),
            ],
        )
        assert "demographics" in feedback.comment
        assert len(feedback.follow_up_queries) == 2

    def test_feedback_without_queries(self):
        """Test CampaignFeedback with no follow-up queries."""
        feedback = CampaignFeedback(
            comment="Research is comprehensive and well-cited",
            follow_up_queries=None,
        )
        assert feedback.follow_up_queries is None

    def test_feedback_default_none(self):
        """Test that follow_up_queries defaults to None."""
        feedback = CampaignFeedback(comment="Good research")
        assert feedback.follow_up_queries is None


class TestMarketingCampaignGuide:
    """Tests for MarketingCampaignGuide schema."""

    def test_valid_campaign_guide(self):
        """Test MarketingCampaignGuide with all fields populated."""
        guide = MarketingCampaignGuide(
            campaign_name="Summer 2026 Launch",
            brand="Nike",
            target_product="Air Max Plus",
            target_audience=["Gen Z", "Millennials", "Athletes"],
            target_regions=["US", "UK", "Japan"],
            campaign_objectives=["Increase brand awareness", "Drive sales"],
            media_strategy=["Social media", "YouTube", "TV"],
            key_selling_points=["Comfort", "Style", "Sustainability"],
        )
        assert guide.brand == "Nike"
        assert len(guide.target_audience) == 3
        assert len(guide.key_selling_points) == 3

    def test_empty_lists_allowed(self):
        """Test that empty lists are accepted for list fields."""
        guide = MarketingCampaignGuide(
            campaign_name="Test",
            brand="TestBrand",
            target_product="Product",
            target_audience=[],
            target_regions=[],
            campaign_objectives=[],
            media_strategy=[],
            key_selling_points=[],
        )
        assert guide.target_audience == []
        assert guide.campaign_objectives == []


class TestInsight:
    """Tests for Insight schema."""

    def test_valid_insight(self):
        """Test Insight with all required fields."""
        insight = Insight(
            insight_title="Gen Z prefers sustainable brands",
            insight_text="Research shows 75% of Gen Z consumers prioritize sustainability",
            insight_urls=["https://example.com/research"],
            key_entities=["Gen Z", "Sustainability", "Consumer behavior"],
            key_relationships=["Gen Z values sustainability over price"],
            key_audiences="Highly relevant for eco-conscious youth demographics",
            key_product_insights="Position product as sustainable alternative",
        )
        assert "Gen Z" in insight.insight_title
        assert len(insight.key_entities) == 3

    def test_multiple_urls(self):
        """Test Insight with multiple source URLs."""
        insight = Insight(
            insight_title="Social Media Trends",
            insight_text="TikTok and Instagram dominate",
            insight_urls=[
                "https://example.com/source1",
                "https://example.com/source2",
                "https://example.com/source3",
            ],
            key_entities=["TikTok", "Instagram"],
            key_relationships=["Both platforms target Gen Z"],
            key_audiences="Social media savvy users",
            key_product_insights="Use short-form video content",
        )
        assert len(insight.insight_urls) == 3


class TestInsights:
    """Tests for Insights collection schema."""

    def test_multiple_insights(self):
        """Test Insights container with multiple items."""
        insights = Insights(
            insights=[
                Insight(
                    insight_title="Trend 1",
                    insight_text="Text 1",
                    insight_urls=["url1"],
                    key_entities=["entity1"],
                    key_relationships=["rel1"],
                    key_audiences="audience1",
                    key_product_insights="insight1",
                ),
                Insight(
                    insight_title="Trend 2",
                    insight_text="Text 2",
                    insight_urls=["url2"],
                    key_entities=["entity2"],
                    key_relationships=["rel2"],
                    key_audiences="audience2",
                    key_product_insights="insight2",
                ),
            ]
        )
        assert len(insights.insights) == 2

    def test_empty_insights_list(self):
        """Test Insights with empty list."""
        insights = Insights(insights=[])
        assert insights.insights == []


class TestYT_Trend:
    """Tests for YT_Trend schema."""

    def test_valid_yt_trend(self):
        """Test YT_Trend with all required fields."""
        trend = YT_Trend(
            video_title="Top 10 Running Shoes 2026",
            trend_text="Video analysis shows Nike dominates",
            trend_urls=["https://youtube.com/watch?v=abc123"],
            key_entities=["Nike", "Running shoes", "Athletes"],
            key_relationships=["Athletes prefer Nike for performance"],
            key_audiences=["Fitness enthusiasts", "Marathon runners"],
            key_product_insights=["Emphasize performance features", "Partner with athletes"],
        )
        assert "Running Shoes" in trend.video_title
        assert len(trend.key_audiences) == 2

    def test_multiple_insights_and_relationships(self):
        """Test YT_Trend with multiple list items."""
        trend = YT_Trend(
            video_title="Fashion Trends 2026",
            trend_text="Analysis of fashion video",
            trend_urls=["https://youtube.com/watch?v=xyz"],
            key_entities=["Fashion", "Streetwear", "Gen Z"],
            key_relationships=["Gen Z drives streetwear trends", "Social media influences fashion"],
            key_audiences=["Young adults", "Fashion enthusiasts", "Trendsetters"],
            key_product_insights=["Use streetwear aesthetics", "Leverage influencer partnerships"],
        )
        assert len(trend.key_relationships) == 2
        assert len(trend.key_product_insights) == 2


class TestYT_Trends:
    """Tests for YT_Trends collection schema."""

    def test_multiple_yt_trends(self):
        """Test YT_Trends container with multiple trends."""
        trends = YT_Trends(
            yt_trends=[
                YT_Trend(
                    video_title="Video 1",
                    trend_text="Text 1",
                    trend_urls=["url1"],
                    key_entities=["entity1"],
                    key_relationships=["rel1"],
                    key_audiences=["aud1"],
                    key_product_insights=["insight1"],
                ),
                YT_Trend(
                    video_title="Video 2",
                    trend_text="Text 2",
                    trend_urls=["url2"],
                    key_entities=["entity2"],
                    key_relationships=["rel2"],
                    key_audiences=["aud2"],
                    key_product_insights=["insight2"],
                ),
            ]
        )
        assert len(trends.yt_trends) == 2


class TestSearch_Trend:
    """Tests for Search_Trend schema."""

    def test_valid_search_trend(self):
        """Test Search_Trend with all required fields."""
        trend = Search_Trend(
            trend_title="Sustainable fashion",
            trend_text="Consumers increasingly prioritize eco-friendly materials",
            trend_urls=["https://trends.google.com/sustainable-fashion"],
            key_entities=["Sustainability", "Fashion", "Consumers"],
            key_relationships=["Consumers demand sustainable fashion", "Brands respond with eco lines"],
            key_audiences=["Eco-conscious shoppers", "Millennials"],
            key_product_insights=["Highlight sustainable materials", "Use eco-friendly messaging"],
        )
        assert trend.trend_title == "Sustainable fashion"
        assert len(trend.key_entities) == 3

    def test_search_trend_with_multiple_sources(self):
        """Test Search_Trend with multiple URL sources."""
        trend = Search_Trend(
            trend_title="AI technology",
            trend_text="AI adoption accelerating across industries",
            trend_urls=[
                "https://source1.com",
                "https://source2.com",
                "https://source3.com",
            ],
            key_entities=["AI", "Technology", "Business"],
            key_relationships=["Businesses adopt AI for efficiency"],
            key_audiences=["Tech professionals", "Business leaders"],
            key_product_insights=["Position as AI-powered solution"],
        )
        assert len(trend.trend_urls) == 3


class TestSearch_Trends:
    """Tests for Search_Trends collection schema."""

    def test_multiple_search_trends(self):
        """Test Search_Trends container with multiple trends."""
        trends = Search_Trends(
            search_trends=[
                Search_Trend(
                    trend_title="Trend 1",
                    trend_text="Text 1",
                    trend_urls=["url1"],
                    key_entities=["e1"],
                    key_relationships=["r1"],
                    key_audiences=["a1"],
                    key_product_insights=["i1"],
                ),
                Search_Trend(
                    trend_title="Trend 2",
                    trend_text="Text 2",
                    trend_urls=["url2"],
                    key_entities=["e2"],
                    key_relationships=["r2"],
                    key_audiences=["a2"],
                    key_product_insights=["i2"],
                ),
            ]
        )
        assert len(trends.search_trends) == 2

    def test_empty_search_trends(self):
        """Test Search_Trends with empty list."""
        trends = Search_Trends(search_trends=[])
        assert trends.search_trends == []
