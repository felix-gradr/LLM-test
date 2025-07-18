from __future__ import annotations
"""Lightweight DuckDuckGo web-search helper.

The function purposely keeps its dependencies limited to the Python standard
library so that it works in most execution sandboxes without extra packages.

The DuckDuckGo *Instant Answer* API is free, does **not** require an API key
and provides JSON responses that are good enough for quick documentation
look-ups or definition searches.
"""

import json
import urllib.parse
import urllib.request
from typing import Dict, List

__all__ = ["duckduckgo_search"]


def duckduckgo_search(query: str, max_results: int = 5) -> Dict[str, object]:
    """Return *max_results* search hits and an abstract for *query*.

    The return schema is:
        {
          "abstract": "<optional text>",
          "results": [
              {"title": "…", "url": "…"},
              …
          ]
        }
    If the request fails (e.g. no internet), an *error* field is set so the
    caller can decide how to proceed.
    """

    url = (
        "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        })
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as fp:
            data = json.loads(fp.read().decode("utf-8"))
    except Exception as exc:  # Network errors, JSON errors, …
        return {"error": str(exc), "abstract": "", "results": []}

    abstract: str = data.get("AbstractText", "")
    results: List[dict] = []

    for topic in data.get("RelatedTopics", []):
        if isinstance(topic, dict) and "Text" in topic and "FirstURL" in topic:
            results.append({"title": topic["Text"], "url": topic["FirstURL"]})
            if len(results) >= max_results:
                break
        # Some entries are nested lists of topics; flatten one level
        if isinstance(topic, dict) and "Topics" in topic:
            for sub in topic.get("Topics", []):
                if (isinstance(sub, dict) and
                        "Text" in sub and "FirstURL" in sub):
                    results.append({"title": sub["Text"], "url": sub["FirstURL"]})
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break

    return {
        "abstract": abstract,
        "results": results,
    }
