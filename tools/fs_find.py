from __future__ import annotations

"""Filesystem search utility for SelfCoder.

This module provides a single high-level function ``fs_find`` that allows
other parts of the agent (or future function-calling interfaces) to quickly
locate files whose *path* **or** *content* matches a given *query* string.

The public API purposefully stays tiny so it is easy to memorise and use
from within LLM prompts while still covering the most common developer
workflows.

Key capabilities
----------------
1. Search by **filename** (e.g. ``fs_find('requirements')``)
2. Search inside **file contents** (e.g. ``fs_find('def my_func')``)
3. **Case-insensitive** by default – toggle via ``case_sensitive=True``
4. **Resource-aware**: skips binary files and caps the amount of data read
5. Returns **structured** results (list[dict]) ready for JSON-serialisation

Examples
~~~~~~~~
>>> from pathlib import Path
>>> results = fs_find('todo', root=Path('.'))
>>> results[0]['path']  # doctest: +SKIP
'notebook.ipynb'

The dictionaries contain at minimum the key ``path``.  If the match occurs
inside the file’s content and *include_content* is *True*, two extra keys are
added:
    • ``line``     – The 1-based line number of the first hit
    • ``snippet``  – A short excerpt (max 120 chars) surrounding the match

The module is *self-contained* with no dependencies beyond the Python
standard library so it works in the constrained execution environment.
"""

from pathlib import Path
from typing import Any, Iterable, List, Sequence
import os
import re
import sys

__all__ = ["fs_find"]

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_TEXT_FILE_EXTS: set[str] = {
    ".py",
    ".md",
    ".txt",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}

_MAX_BYTES_TO_READ = 2 * 1024 * 1024  # 2 MB safety cap per file
_SNIPPET_RADIUS = 60  # characters left & right of match when building snippet


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fs_find(
    query: str,
    *,
    root: str | Path = Path("."),
    case_sensitive: bool = False,
    include_content: bool = True,
    max_results: int | None = None,
) -> List[dict[str, Any]]:
    """Search *root* recursively for *query*.

    Parameters
    ----------
    query
        Sub-string to look for either in the filename (including relative
        parts) **or** inside file contents.
    root
        Directory that acts as the search root.  Default is the current
        working directory.  Accepts ``str`` or ``pathlib.Path``.
    case_sensitive
        If *True* the search is performed case-sensitively.  The default is
        *False* – everything is lower-cased for matching.
    include_content
        Whether to include ``line`` and ``snippet`` keys when a content match
        is found.  Setting it to *False* can save memory when only the file
        paths are required.
    max_results
        Optional upper bound on the number of matches returned.  ``None``
        means unbounded.

    Returns
    -------
    list[dict]
        Sorted list of match dictionaries.  Filename hits come first ordered
        alphabetically, followed by content hits ordered by path then line.
    """

    if not query:
        return []  # trivial guard – empty query returns nothing

    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    # Pre-compute case-folded query if needed
    _query_cmp = query if case_sensitive else query.lower()

    filename_hits: list[dict[str, Any]] = []
    content_hits: list[dict[str, Any]] = []

    for file_path in _iter_files(root):
        # ------------------------------------------------------------------
        # 1) Filename matching
        # ------------------------------------------------------------------
        rel_path_str = str(file_path.relative_to(root))
        rel_path_cmp = rel_path_str if case_sensitive else rel_path_str.lower()
        if _query_cmp in rel_path_cmp:
            filename_hits.append({"path": rel_path_str})
            if max_results is not None and len(filename_hits) >= max_results:
                # We cannot early-exit completely because content matches could
                # still be needed if filename hits < max_results – continue.
                pass

        # ------------------------------------------------------------------
        # 2) Content matching (skip if limit already satisfied)
        # ------------------------------------------------------------------
        if max_results is not None and len(filename_hits) + len(content_hits) >= max_results:
            continue

        if not _looks_textual(file_path):
            continue  # binary or unknown – skip

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")[:_MAX_BYTES_TO_READ]
        except Exception:
            # Any issue while reading – ignore this file for content search
            continue

        text_cmp = text if case_sensitive else text.lower()
        idx = text_cmp.find(_query_cmp)
        if idx != -1:
            line_no = text_cmp.count("\n", 0, idx) + 1  # 1-based line number
            if include_content:
                start = max(0, idx - _SNIPPET_RADIUS)
                end = min(len(text), idx + len(query) + _SNIPPET_RADIUS)
                snippet = text[start:end].replace("\n", " ")
                content_hits.append({
                    "path": rel_path_str,
                    "line": line_no,
                    "snippet": snippet,
                })
            else:
                content_hits.append({"path": rel_path_str})

            if max_results is not None and len(filename_hits) + len(content_hits) >= max_results:
                continue

    # Combine results – deterministic ordering for reproducibility
    filename_hits.sort(key=lambda d: d["path"])
    content_hits.sort(key=lambda d: (d["path"], d.get("line", 0)))
    results: list[dict[str, Any]] = filename_hits + content_hits
    if max_results is not None:
        results = results[:max_results]
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iter_files(root: Path) -> Iterable[Path]:
    """Yield *regular* files found below *root* – depth-first."""
    # Using os.walk so we can optionally ignore directories later
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            yield Path(dirpath) / fname


def _looks_textual(path: Path) -> bool:
    """Heuristic to decide whether *path* is a text file."""
    if path.suffix.lower() in _TEXT_FILE_EXTS:
        return True

    try:
        with path.open("rb") as fh:
            sample = fh.read(8000)
        # If the sample contains NUL bytes it is almost certainly binary
        return b"\x00" not in sample
    except Exception:
        # Any IO error – assume binary to be safe
        return False
