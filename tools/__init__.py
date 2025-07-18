from __future__ import annotations
"""Utility tool-set for SelfCoder.

This package hosts helper functions ("tools") that the agent can invoke at
runtime.  The *registry* dictionary maps a **tool name** to a **callable**.  Any
module can register a new tool via the `@register` decorator:

    from tools import register

    @register()               # Registers under function name
    def my_helper(arg1: str):
        ...

    @register("fancy_name")   # Explicit registry key
    def another_tool():
        ...

The root agent then accesses the mapping through

    from tools import registry as TOOL_REGISTRY
"""

from importlib import import_module
from typing import Callable, Dict

__all__ = ["registry", "register"]

# ---------------------------------------------------------------------------
# Public registry & decorator
# ---------------------------------------------------------------------------

registry: Dict[str, Callable] = {}


def register(name: str | None = None):
    """Decorator to add *func* to the global *registry* under *name*.

    If *name* is omitted, the function's `__name__` attribute is used.
    """

    def decorator(func: Callable) -> Callable:  # type: ignore[override]
        key = name or func.__name__
        if key in registry:
            # Overwrites are allowed but emit a gentle warning to stderr.
            import sys

            print(f"[tools.register] WARNING: overwriting existing tool '{key}'.", file=sys.stderr)
        registry[key] = func
        return func

    # Support both `@register` and `@register("custom")` syntaxes
    if callable(name):  # Used without parentheses – name is actually the func
        func = name  # type: ignore[assignment]
        name = None
        return decorator(func)  # type: ignore[arg-type]

    return decorator


# ---------------------------------------------------------------------------
# Auto-import core tools so they self-register
# ---------------------------------------------------------------------------

# Importing a module that uses the @register decorator has the side-effect of
# populating *registry*.  Keep the list small to avoid unnecessary overhead –
# additional tools can be imported ad-hoc when needed.
for _module in (
    "tools.web_search",
):
    try:
        import_module(_module)
    except Exception as _exc:  # pragma: no cover – tolerate missing deps / net
        import sys

        print(f"[tools] Failed to import {_module}: {_exc}", file=sys.stderr)
