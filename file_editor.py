"""file_editor.py
High-level helpers for surgical edits to text files.
These functions avoid rewriting the entire file whenever possible,
making iterative self-modification cheaper and less error-prone.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Iterable, Callable

__all__ = [
    "insert_after",
    "replace_block",
    "replace_regex",
    "ensure_line",
]

def _read(path: Path) -> list[str]:
    """Load file as list of lines (keep line endings)."""
    return path.read_text(encoding="utf-8").splitlines(keepends=True)

def _write(path: Path, lines: Iterable[str]) -> None:
    """Write back only if changed to reduce unnecessary churn."""
    new_text = "".join(lines)
    if path.exists():
        old_text = path.read_text(encoding="utf-8")
        if old_text == new_text:
            return
    path.write_text(new_text, encoding="utf-8")


# ---------------------------------------------------------------------- #
#  Public helpers
# ---------------------------------------------------------------------- #

def insert_after(path: str | Path, anchor: str | re.Pattern[str], snippet: str) -> bool:
    """Insert *snippet* (with newline) immediately after first line matching *anchor*.
    Returns True if mutation happened.
    """
    path = Path(path)
    lines = _read(path)
    for i, line in enumerate(lines):
        if (isinstance(anchor, str) and anchor in line) or (
            isinstance(anchor, re.Pattern) and anchor.search(line)
        ):
            lines.insert(i + 1, snippet + ("\n" if not snippet.endswith("\n") else ""))
            _write(path, lines)
            return True
    return False


def replace_block(
    path: str | Path,
    start_marker: str,
    end_marker: str,
    new_block: str,
    include_markers: bool = False,
) -> bool:
    """Replace everything between *start_marker* and *end_marker*.
    If *include_markers* is True, the markers themselves are also replaced.
    Returns True if mutation happened.
    """
    path = Path(path)
    lines = _read(path)
    start_idx = end_idx = None
    for i, line in enumerate(lines):
        if start_idx is None and start_marker in line:
            start_idx = i
        elif start_idx is not None and end_marker in line:
            end_idx = i
            break

    if start_idx is None or end_idx is None or start_idx >= end_idx:
        return False  # markers not found

    if include_markers:
        slice_start, slice_end = start_idx, end_idx + 1
    else:
        slice_start, slice_end = start_idx + 1, end_idx

    new_lines = new_block.splitlines(keepends=True)
    if not new_block.endswith("\n"):
        new_lines[-1] += "\n"

    mutated = lines[:slice_start] + new_lines + lines[slice_end:]
    _write(path, mutated)
    return True


def replace_regex(path: str | Path, pattern: str | re.Pattern[str], repl: str | Callable[[re.Match[str]], str]) -> int:
    """Regex replace inside *path*. Returns number of substitutions."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, repl, text)
    if n:
        path.write_text(new_text, encoding="utf-8")
    return n


def ensure_line(path: str | Path, line: str) -> bool:
    """Append *line* (with newline) if it doesn't already exist."""
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if line not in text:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + ("\n" if not line.endswith("\n") else ""))
        return True
    return False
