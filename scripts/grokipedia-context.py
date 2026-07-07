#!/usr/bin/env python3
"""Fetch Grokipedia articles for a decision subject."""

import json
import sys
import time
from pathlib import Path

try:
    from grokipedia_api import GrokipediaClient
except ImportError:
    GrokipediaClient = None

BASE_URL = "https://grokipedia.com"


def search_grokipedia(query: str, limit: int = 3) -> dict:
    start = time.perf_counter()

    if GrokipediaClient is None:
        return {
            "subject": query,
            "hit": False,
            "articles": [],
            "error": "Install grokipedia-api: pip install grokipedia-api",
            "retrieval_latency_ms": round((time.perf_counter() - start) * 1000),
        }

    try:
        with GrokipediaClient() as client:
            results = client.search(query, limit=limit)
            articles = []

            for item in results.get("results", [])[:limit]:
                slug = item.get("slug", "")
                articles.append({
                    "type": "grokipedia",
                    "title": item.get("title", slug.replace("_", " ")),
                    "slug": slug,
                    "url": f"{BASE_URL}/page/{slug}",
                    "snippet": item.get("snippet", ""),
                })

            latency = round((time.perf_counter() - start) * 1000)
            return {
                "subject": query,
                "hit": len(articles) > 0,
                "articles": articles,
                "retrieval_latency_ms": latency,
                "grokipedia_hit_rate": 1.0 if articles else 0.0,
            }
    except Exception as e:
        return {
            "subject": query,
            "hit": False,
            "articles": [],
            "error": str(e),
            "retrieval_latency_ms": round((time.perf_counter() - start) * 1000),
        }


def main():
    if len(sys.argv) > 1:
        subject = " ".join(sys.argv[1:])
    else:
        data = json.load(sys.stdin)
        subject = data.get("subject", "")

    if not subject.strip():
        print(json.dumps({"error": "Subject is required.", "hit": False}))
        sys.exit(1)

    result = search_grokipedia(subject.strip())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()