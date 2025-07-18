from __future__ import annotations
"""Lightweight DuckDuckGo web-search helper.

The function purposely keeps its dependencies limited to the Python standard
library so that it works in most execution sandboxes without extra packages.
The DuckDuckGo *Instant Answer* API is free, does **not** require an API key
and provides JSON responses that are good enough for quick documentation look-
ups or definition searches.
"""

import json
import urllib.parse
import urllib.request
from typing import Dict, List

from . import register  # Self-registration decorator

__all__ = ["duckduckgo_search"]


@register("duckduckgo_search")
def duckduckgo_search(query: str, max_results: int = 5) -> Dict[str, object]:
    """Return *max_results* search hits and an abstract for *query*.

    The return schema is::
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

    endpoint = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
    )

    try:
        with urllib.request.urlopen(endpoint, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover – network issues, etc.
        return {"error": str(exc)}

    abstract: str = payload.get("AbstractText", "")
    related: List[Dict[str, str]] = []

    # The API returns a flat list *or* a nested "RelatedTopics" structure.
    candidates = payload.get("Results") or payload.get("RelatedTopics", [])
    for item in candidates:
        if isinstance(item, dict) and "FirstURL" in item:
            related.append({"title": item.get("Text", ""), "url": item["FirstURL"]})
            if len(related) >= max_results:
                break

    return {"abstract": abstract, "results": related}
