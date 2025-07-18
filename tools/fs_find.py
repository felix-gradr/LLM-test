from __future__ import annotations

"""Filesystem search utility for SelfCoder.

This module provides a single high-level function ``fs_find`` that allows other
parts of the agent (or future function-calling interfaces) to quickly discover
files matching a substring or regular-expression pattern.

Rationale
---------
Self-improvement often requires locating existing code or documentation that
contains a given symbol, function name or phrase. While Python's ``Path.rglob``
can be used directly, wrapping this logic gives us:

1. Consistent filtering (e.g., ignore ``.git``/virtual-env directories).
2. Easy extensibility (future ranking, embedding search, etc.).
3. A stable interface we can expose to an LLM function-calling schema later.

API
---
    fs_find(pattern: str,
            root: str | Path = ".",
            case_sensitive: bool = False,
            include_content: bool = False,
            max_results: int | None = 50) -> list[dict[str, str]]

Returns a list of dicts. Each dict has at least the key ``path``.
If ``include_content`` is True, it will additionally contain ``content`` with
the full file text (truncated to 8 kB to stay reasonable).
"""

from pathlib import Path
import re
from typing import List, Dict, Union, Optional

__all__ = ["fs_find"]

# Filetypes that are safe/textual enough to inspect.  You can extend this.
_TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
}

# Directories to skip during traversal
_SKIP_DIRS = {".git", "__pycache__", ".venv", "env", "venv", "node_modules"}

_MAX_CONTENT_PREVIEW = 8 * 1024  # 8 kB


def _iter_files(root: Path):
    """Yield candidate files under *root* honoring _SKIP_DIRS / _TEXT_EXTENSIONS."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(seg in _SKIP_DIRS for seg in path.parts):
            continue
        if path.suffix.lower() not in _TEXT_EXTENSIONS:
            continue
        yield path


def fs_find(
    pattern: str,
    root: Union[str, Path] = ".",
    *,
    case_sensitive: bool = False,
    include_content: bool = False,
    max_results: Optional[int] = 50,
) -> List[Dict[str, str]]:
    """Search *root* for files whose **content** OR **path** matches *pattern*.

    Parameters
    ----------
    pattern : str
        Substring (or regex) to search for.
    root : str | Path, default "."
        Directory to start searching from.
    case_sensitive : bool, default False
        If False, the search will be case-insensitive (pattern lowered).
    include_content : bool, default False
        When True, include file text (truncated) in each result dict.
    max_results : int | None, default 50
        Maximum number of results to return. ``None`` means unlimited.
    """
    root = Path(root).expanduser().resolve()
    results: List[Dict[str, str]] = []

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error:
        # Treat as literal substring
        regex = None
        if not case_sensitive:
            pattern = pattern.lower()

    for path in _iter_files(root):
        # First, match against the relative path string
        rel_str = str(path.relative_to(root))
        haystack_path = rel_str if case_sensitive else rel_str.lower()
        matched = False
        if regex:
            matched = bool(regex.search(rel_str))
        else:
            matched = pattern in haystack_path

        # If not matched by path, check content (cheap substring or regex)
        if not matched:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue  # skip unreadable/binary
            haystack_content = text if case_sensitive else text.lower()
            if regex:
                matched = bool(regex.search(text))
            else:
                matched = pattern in haystack_content

        if matched:
            entry: Dict[str, str] = {"path": rel_str}
            if include_content:
                try:
                    snippet = path.read_text(encoding="utf-8", errors="ignore")[:_MAX_CONTENT_PREVIEW]
                except Exception:
                    snippet = ""
                entry["content"] = snippet
            results.append(entry)

        if max_results is not None and len(results) >= max_results:
            break

    return results