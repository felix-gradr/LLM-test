"""Utility tool-set for SelfCoder.

This package hosts helper functions ("tools") that the agent can invoke at
runtime.  Additional tools should be added to *registry.py* so that they are
automatically discoverable by the *call_tool* action.
"""

from .registry import TOOL_REGISTRY  # noqa: F401 – re-export for convenience

# Keep the namespace clean – consumers should use the *call_tool* pattern via
# the orchestrator instead of importing individual helpers directly.
__all__ = ["TOOL_REGISTRY"]
