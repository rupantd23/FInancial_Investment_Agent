import os
import unittest
from unittest.mock import patch

from news import GNewsNotConfigured, GNewsRequestFailed, normalize_article, search_news


class NewsTests(unittest.TestCase):
    def test_normalizes_gnews_article_and_marks_it_pull_excluded(self):
        article = normalize_article(
            {
                "title": "Company update",
                "description": "Description",
                "url": "https://example.com/article",
                "publishedAt": "2026-11-14T08:00:00Z",
                "source": {"name": "Example News", "url": "https://example.com", "country": "in"},
            }
        )
        self.assertEqual(article["source"]["name"], "Example News")
        self.assertFalse(article["useInPull"])
        self.assertEqual(article["provenance"], "GNews API")

    def test_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GNewsNotConfigured):
                search_news("TCS")

    @patch.dict(os.environ, {"GNEWS_API_KEY": "test-key"}, clear=True)
    @patch("news.requests.get")
    def test_network_failure_is_reported_without_leaking_provider_details(self, get):
        import requests

        get.side_effect = requests.ConnectionError("provider unavailable")
        with self.assertRaises(GNewsRequestFailed):
            search_news("TCS")


if __name__ == "__main__":
    unittest.main()
