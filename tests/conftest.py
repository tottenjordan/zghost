"""Pytest configuration and shared fixtures for zghost tests."""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run."""
    # Set minimal required env vars for imports to work
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT_NUMBER", "123456789")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    os.environ.setdefault("BUCKET", "test-bucket")
    os.environ.setdefault("YT_SECRET_MNGR_NAME", "test-yt-secret")
    os.environ.setdefault("ENABLE_LLM_STATUS", "false")  # Disable LLM status for tests

    yield

    # Cleanup (if needed)
    pass


@pytest.fixture(scope="session")
def mock_secrets():
    """Mock the secrets manager for testing."""
    with patch("trends_and_insights_agent.shared_libraries.secrets.access_secret_version") as mock_secret:
        mock_secret.return_value = "fake-api-key-for-testing"
        yield mock_secret


@pytest.fixture(scope="session", autouse=True)
def mock_youtube_client():
    """Mock YouTube API client to avoid API calls in tests."""
    with patch("trends_and_insights_agent.tools.youtube_client") as mock_client:
        # Create a mock client with basic structure
        mock_client.search.return_value.list.return_value.execute.return_value = {
            "items": []
        }
        yield mock_client


@pytest.fixture(scope="session", autouse=True)
def mock_genai_client():
    """Mock Google GenAI client to avoid API calls in tests."""
    with patch("trends_and_insights_agent.tools.client") as mock_client:
        # Create a mock response
        mock_response = Mock()
        mock_response.text = "Mock AI response"
        mock_client.models.generate_content.return_value = mock_response
        yield mock_client


@pytest.fixture
def sample_campaign_guide():
    """Provide a sample MarketingCampaignGuide for testing."""
    from trends_and_insights_agent.shared_libraries.schema_types import (
        MarketingCampaignGuide,
    )

    return MarketingCampaignGuide(
        campaign_name="Test Campaign 2026",
        brand="TestBrand",
        target_product="TestProduct",
        target_audience=["Young professionals", "Tech enthusiasts"],
        target_regions=["US", "Canada"],
        campaign_objectives=["Increase awareness", "Drive sales"],
        media_strategy=["Social media", "YouTube"],
        key_selling_points=["Innovation", "Quality", "Value"],
    )


@pytest.fixture
def sample_insight():
    """Provide a sample Insight for testing."""
    from trends_and_insights_agent.shared_libraries.schema_types import Insight

    return Insight(
        insight_title="Test Insight",
        insight_text="This is a test insight about market trends",
        insight_urls=["https://example.com/source"],
        key_entities=["Entity1", "Entity2"],
        key_relationships=["Relationship1"],
        key_audiences="Target audience insights",
        key_product_insights="Product positioning insights",
    )


@pytest.fixture
def sample_yt_trend():
    """Provide a sample YT_Trend for testing."""
    from trends_and_insights_agent.shared_libraries.schema_types import YT_Trend

    return YT_Trend(
        video_title="Test Video Title",
        trend_text="Test trend analysis",
        trend_urls=["https://youtube.com/watch?v=test"],
        key_entities=["Entity1"],
        key_relationships=["Relationship1"],
        key_audiences=["Audience1"],
        key_product_insights=["Insight1"],
    )


@pytest.fixture
def sample_search_trend():
    """Provide a sample Search_Trend for testing."""
    from trends_and_insights_agent.shared_libraries.schema_types import Search_Trend

    return Search_Trend(
        trend_title="Test Search Trend",
        trend_text="Test search analysis",
        trend_urls=["https://trends.google.com/test"],
        key_entities=["Entity1"],
        key_relationships=["Relationship1"],
        key_audiences=["Audience1"],
        key_product_insights=["Insight1"],
    )


@pytest.fixture
def mock_callback_context():
    """Provide a mock CallbackContext for testing callbacks."""
    from unittest.mock import Mock

    context = Mock()
    context.agent_name = "test_agent"
    context.state = {}
    context.user_content = None
    return context


@pytest.fixture
def mock_tool_context():
    """Provide a mock ToolContext for testing tool callbacks."""
    from unittest.mock import Mock

    context = Mock()
    context.state = {}
    return context


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location/name."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid or "e2e" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        # Mark slow tests
        if "agent_imports" in item.nodeid or "root_agent" in str(item.function):
            item.add_marker(pytest.mark.slow)
        # Mark unit tests (everything else)
        else:
            item.add_marker(pytest.mark.unit)
