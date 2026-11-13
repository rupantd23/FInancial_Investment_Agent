import os
import unittest
from unittest.mock import patch

from news import GNewsNotConfigured, normalize_article, search_news


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


if __name__ == "__main__":
    unittest.main()
