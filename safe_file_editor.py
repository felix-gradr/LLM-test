"""Safety shim automatically installed by the upgrade script.

All public callables from `file_editor` are wrapped so that if they raise
an exception, we transparently retry the same call via `fallback_editor`.

Importing this module has the side-effect of monkey-patching `file_editor`
in-place, so downstream code can keep using `import file_editor` without
modification.
"""

from __future__ import annotations

import functools
import logging
import traceback
from types import FunctionType
from typing import Any, Callable

try:
    import file_editor  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError("file_editor must be importable for safe patching") from e

try:
    import fallback_editor  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError("fallback_editor must be importable for safe patching") from e

_logger = logging.getLogger("safe_file_editor")

def _make_wrapper(name: str, primary: Callable[..., Any], backup: Callable[..., Any]):
    """Return a function that falls back on failure."""

    @functools.wraps(primary)
    def _wrapper(*args: Any, **kwargs: Any):  # noqa: ANN401
        try:
            return primary(*args, **kwargs)
        except Exception as err:  # pragma: no cover
            _logger.warning(
                "file_editor.%s failed, retrying with fallback_editor.%s – %s",
                name,
                name,
                err,
            )
            _logger.debug("Traceback:\n%s", traceback.format_exc())
            return backup(*args, **kwargs)

    return _wrapper

def _monkey_patch() -> None:
    """Patch all shared callables in file_editor with safe fallbacks."""
    for attr_name in dir(file_editor):
        if attr_name.startswith("_"):
            continue

        primary_attr = getattr(file_editor, attr_name)
        backup_attr = getattr(fallback_editor, attr_name, None)

        if callable(primary_attr) and callable(backup_attr):
            patched = _make_wrapper(attr_name, primary_attr, backup_attr)
            setattr(file_editor, attr_name, patched)

_monkey_patch()
