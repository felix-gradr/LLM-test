from __future__ import annotations

"""Filesystem search utility for SelfCoder.

This module exposes a single helper ``fs_find`` which performs a very fast
and *easy-to-use* recursive search through the project directory.  It is
intended for interactive use inside prompts (for example, when the agent wants
to quickly locate where in the repository a certain symbol or string appears)
as well as for programmatic use by other internal tools.

The public surface area purposefully remains tiny so that it is easy to
over-fit in the LLM-context and therefore *memorisable* for the agent in later
iterations.

Key features
------------
1. Search by **path / filename** – e.g. ``fs_find('requirements')`` will match
   ``requirements.txt`` as well as files within a ``requirements/`` folder.
2. Optional **content scan** – by default the function will look inside files
   as well.  This can be disabled via ``include_content=False`` to speed up
   large directory searches.
3. **Case-insensitive** by default – because that is the behaviour a human
   usually expects when quickly looking for *something*.
4. **Streaming-friendly** – returns a list of *plain dicts* that are easily
   serialisable into JSON and therefore safe to embed in the model prompt.

The implementation is intentionally kept dependency-free (uses only stdlib)
so that it keeps working in the highly sandboxed execution environment.
"""

from pathlib import Path
from typing import Iterable, List, Dict, Union, Any

__all__ = [
    "fs_find",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_files(root: Path) -> Iterable[Path]:
    """Yield *all* regular files below *root* (recursively).

    This skips symbolic links and directories for safety/performance.
    """
    # Using Path.rglob is significantly faster than os.walk for large trees
    # because it executes in C inside CPython.
    yield from (p for p in root.rglob("*") if p.is_file())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fs_find(
    query: str,
    *,
    root: Union[str, Path] = Path("."),
    include_content: bool = True,
    case_sensitive: bool = False,
    max_results: int | None = None,
) -> List[Dict[str, Any]]:
    """Search *root* recursively for the first *max_results* matches of *query*.

    Parameters
    ----------
    query:
        The needle to look for.  This can be a filename fragment (e.g. ``"foo"``)
        or – if ``include_content`` is True – an arbitrary string that you
        expect to appear *inside* a file.
    root:
        Directory where the search should begin.  Defaults to the current
        working directory.  Accepts both ``Path`` and ``str`` for convenience.
    include_content:
        Also open each text file and look for *query* within its content.
        Set this to ``False`` when only the filename/location matters – this
        makes the search significantly quicker for large repositories.
    case_sensitive:
        Controls whether the match is case-sensitive.  The default (``False``)
        is usually what a human expects when they *forget* about exact casing.
    max_results:
        If given, stop the search once this many results have been found.  This
        is important to avoid blowing up prompt sizes when the query is very
        generic (like ``"the"``).

    Returns
    -------
    list[dict]
        Each element contains at least the key ``"path"`` with a *string*
        representation of the **relative** path (to *root*).
    """

    # Normalise inputs -------------------------------------------------------
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"Search root does not exist or is not a directory: {root}")

    # Normalise query according to case mode
    needle = query if case_sensitive else query.lower()

    results: List[Dict[str, Any]] = []

    # Traverse the tree ------------------------------------------------------
    for file_path in _iter_files(root_path):
        try:
            rel_path_str = str(file_path.relative_to(root_path))
        except ValueError:
            # Very unlikely, but guard against path traversal oddities
            rel_path_str = str(file_path)

        haystack_name = rel_path_str if case_sensitive else rel_path_str.lower()

        # 1) Match against filename / path ----------------------------------
        match_found = needle in haystack_name

        # 2) Optionally match against file content ---------------------------
        if not match_found and include_content:
            # We do a *fast* string search – reading the whole file at once is
            # okay for <1MB files.  For bigger files we chunk-read.
            try:
                with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
                    if not case_sensitive:
                        # Lowercase line by line to avoid allocating huge string
                        for line in fh:
                            if needle in line.lower():
                                match_found = True
                                break
                    else:
                        for line in fh:
                            if needle in line:
                                match_found = True
                                break
            except (OSError, UnicodeDecodeError):
                # Binary or unreadable – silently ignore for content scanning.
                pass

        if match_found:
            results.append({"path": rel_path_str})
            if max_results is not None and len(results) >= max_results:
                break

    return results
