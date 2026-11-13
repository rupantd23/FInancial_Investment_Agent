"""Server-side GNews integration for contextual investor news."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class GNewsNotConfigured(RuntimeError):
    pass


def normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    source = article.get("source") or {}
    return {
        "id": article.get("id"),
        "title": article.get("title", "Untitled article"),
        "description": article.get("description"),
        "content": article.get("content"),
        "url": article.get("url"),
        "image": article.get("image"),
        "publishedAt": article.get("publishedAt"),
        "source": {
            "name": source.get("name"),
            "url": source.get("url"),
            "country": source.get("country"),
        },
        "provenance": "GNews API",
        "useInPull": False,
    }


def search_news(
    query: str,
    *,
    lang: str = "en",
    country: str = "in",
    max_results: int = 10,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("GNEWS_API_KEY")
    if not api_key:
        raise GNewsNotConfigured("GNEWS_API_KEY is not set")
    if not query.strip():
        raise ValueError("News query cannot be empty")

    params: dict[str, Any] = {
        "q": query[:200],
        "lang": lang,
        "country": country,
        "max": max(1, min(max_results, 10)),
        "sortby": "publishedAt",
        "in": "title,description",
    }
    if from_date:
        params["from"] = from_date.isoformat()
    if to_date:
        params["to"] = to_date.isoformat()

    response = requests.get(
        "https://gnews.io/api/v4/search",
        params=params,
        headers={"X-Api-Key": api_key},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "query": query,
        "totalArticles": payload.get("totalArticles", 0),
        "articles": [normalize_article(article) for article in payload.get("articles", [])],
        "provenance": "GNews API",
        "useInPull": False,
        "notice": "News is contextual only and is excluded from Pull analysis.",
    }
