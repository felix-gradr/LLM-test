from __future__ import annotations

"""Filesystem search utility for SelfCoder.

This module provides a single high-level function ``fs_find`` that allows
other parts of the agent (or future function-calling interfaces) to quickly
locate files whose *path* or *content* matches a given query string.

The implementation purposefully keeps the public interface *very small* so
that it is easy to memorise and use from LLM prompts while still being
powerful enough for day-to-day coding assistance.

Key capabilities
----------------
1. Search by **filename/path** substring.
2. Optional search within **file contents**.
3. **Case-insensitive** matching by default – can be toggled.
4. Graceful handling of binary / non-UTF8 files.
5. Returns a *list of dictionaries* ready for JSON-serialisation so the caller
   can easily feed results back into an LLM conversation.

The public API purposefully does **not** try to be a full grep/ag search
replacement – it only needs to satisfy the agent's immediate requirements and
unit tests.  New features can be added incrementally as the need arises.
"""

from pathlib import Path
from typing import Iterable, List, Dict, Optional

__all__ = ["fs_find"]


def _iter_files(root: Path, extensions: Optional[Iterable[str]] = None):
    """Yield all files under *root* recursively, filtered by *extensions*.

    *extensions* – an iterable of lowercase extensions (with the leading dot),
    or *None* to allow all file types.
    """
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if extensions is not None and path.suffix.lower() not in extensions:
            continue
        yield path


def _match(haystack: str, needle: str, case_sensitive: bool) -> bool:
    """Return True if *needle* is present in *haystack* using the given case rules."""
    if case_sensitive:
        return needle in haystack
    return needle.lower() in haystack.lower()


def fs_find(
    query: str,
    *,
    root: Path | str = Path("."),
    include_content: bool = True,
    case_sensitive: bool = False,
    max_results: int | None = None,
    file_extensions: Iterable[str] | None = None,
) -> List[Dict[str, str]]:
    """Search *root* for files matching *query*.

    Parameters
    ----------
    query : str
        Sub-string to search for.  (Regex not yet supported.)
    root : Path | str, default ``Path('.')``
        Directory to search.  Accepts both ``str`` and ``Path`` objects.
    include_content : bool, default ``True``
        When *True* the function also searches inside file contents.
    case_sensitive : bool, default ``False``
        Perform a case-sensitive match when *True*.
    max_results : int | None, default ``None``
        Optional cap on the number of matches returned.
    file_extensions : Iterable[str] | None, default ``None``
        Restrict the search to the given (lower-case) extensions *including* the
        leading dot.  ``None`` means "all extensions".

    Returns
    -------
    list[dict]
        Each dict contains at minimum the key ``"path"`` (relative to *root*).
        When ``include_content=True`` an additional key ``"snippet"`` is
        present containing a short excerpt surrounding the first match.
    """

    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    # Normalise *file_extensions* to a set of lowercase strings starting with '.'
    if file_extensions is not None:
        file_extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in file_extensions}

    results: List[Dict[str, str]] = []

    def _add_result(file: Path, snippet: str | None = None):
        entry: Dict[str, str] = {"path": str(file.relative_to(root_path))}
        if snippet is not None:
            entry["snippet"] = snippet
        results.append(entry)

    for file in _iter_files(root_path, file_extensions):
        # Check filename / relative path first (fast path)
        rel_str = str(file.relative_to(root_path))
        if _match(rel_str, query, case_sensitive):
            _add_result(file)
        elif include_content:
            # Try reading file content ‑ skip if binary or very large
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                # If the file cannot be read as text, skip it.
                continue

            if _match(text, query, case_sensitive):
                # Produce a short snippet (~60 chars around the first occurrence)
                idx = (text if case_sensitive else text.lower()).find(query if case_sensitive else query.lower())
                start = max(idx - 30, 0)
                end = min(idx + len(query) + 30, len(text))
                snippet = text[start:end].replace("\n", " ")
                _add_result(file, snippet=snippet)

        if max_results is not None and len(results) >= max_results:
            break

    return results
