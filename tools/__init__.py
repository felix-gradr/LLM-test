"""Utility tool-set for SelfCoder.

This package hosts helper functions ("tools") that the agent can invoke at
runtime.  Additional tools should be added here and imported in *root.py* so
that the LLM can call them through the dedicated *action* system.
"""

from .web_search import duckduckgo_search  # Re-export for convenience
