# Unit tests for youtube and web LLM tools

import unittest

from trends_and_insights_agent.tools import query_youtube_api, query_web
from trends_and_insights_agent.common_agents.trend_assistant.tools import (
    get_youtube_trends,
)
import asyncio


# unit test for query web
class YT_Web_Tools(unittest.TestCase):
    def test_query_web(self):
        # test query web
        query = "what is the latest in AI"
        response = asyncio.run(query_web(query=query, num_results=1))
        self.assertIsNot(response, None)
        self.assertIsNot(response[0].get("website_text"), None)

    def test_query_youtube_api(self):
        # test query youtube api
        query = "what is the latest in AI"
        response = query_youtube_api(
            query=query, region_code="US", video_duration="any"
        )
        self.assertIsNot(response, None)
        self.assertIsNot(response.get("items"), None)

    def test_get_youtube_trends(self):
        # test get youtube trends
        response = get_youtube_trends(region_code="US")
        self.assertIsNot(response, None)
        self.assertIsNot(response.get("items"), None)
