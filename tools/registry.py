from __future__ import annotations
"""Generic registry that exposes *callable* tools to SelfCoder.

Each entry maps a **unique string key** → **callable** that can be invoked via
```
{
  "action": "call_tool",
  "tool": "<key>",
  "args": {"kw": "values"}
}
```
The *root.py* orchestrator will look-up the key in this dictionary and pass the
*args* along.  All tools **must** be synchronous for now – if we need async in
future iterations we can extend the mechanism.
"""

from typing import Dict, Callable, Any

# ---------------------------------------------------------------------------
# Import individual tool helpers and expose them here
# ---------------------------------------------------------------------------
from .web_search import duckduckgo_search  # noqa: E402

TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "duckduckgo_search": duckduckgo_search,
}

# Convenience re-export so callers can do `from tools.registry import TOOL_REGISTRY`
__all__ = ["TOOL_REGISTRY"]
