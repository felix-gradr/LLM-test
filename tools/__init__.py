"""Utility tool-set for SelfCoder.

This package hosts helper functions ("tools") that the agent can invoke at
runtime.  Additional tools should be added here and imported in *root.py* so
that the LLM can call them through the dedicated *action* system.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from .web_search import duckduckgo_search  # Re-export for convenience

# ---------------------------------------------------------------------------
# Public registry – maps tool names (str) to callables.  *root.py* relies on it
# for the generic `call_tool` action so **always** register a new helper here.
# ---------------------------------------------------------------------------
registry: Dict[str, Callable[..., Any]] = {
    "duckduckgo_search": duckduckgo_search,
}

__all__ = [
    "duckduckgo_search",
    "registry",
]
