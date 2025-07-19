
"""
fallback_editor.py

A **very** small, dependency-free substitute for `file_editor.py`.
If the primary editing utilities ever break, SelfCoder can import this
module instead and continue patching its own code base.

Public API (mirrors the core helpers of file_editor):
    _read(path)                        -> str
    _write(path, text)                 -> None
    insert_after(path, anchor, snip)   -> bool
    replace_block(path, start, end, block) -> bool
    replace_regex(path, pattern, repl) -> bool
    ensure_line(path, line)            -> bool
"""

from __future__ import annotations

import re
from pathlib import Path


# ------------------------------------------------------------------ #
# Low-level helpers
# ------------------------------------------------------------------ #
def _read(path: str | Path) -> str:
    """Read text from *path* in UTF-8."""
    return Path(path).read_text(encoding='utf-8')


def _write(path: str | Path, text: str) -> None:
    """Write *text* to *path* in UTF-8, creating parents if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


# ------------------------------------------------------------------ #
# High-level editing helpers
# ------------------------------------------------------------------ #
def insert_after(path: str | Path, anchor: str, snippet: str) -> bool:
    """Insert *snippet* right after the first occurrence of *anchor*."""
    content = _read(path)
    idx = content.find(anchor)
    if idx == -1:
        return False

    # position after end-of-line
    eol = content.find('\n', idx)
    eol = len(content) if eol == -1 else eol + 1
    new_content = content[:eol] + snippet + content[eol:]

    if new_content != content:
        _write(path, new_content)
        return True
    return False


def replace_block(
    path: str | Path,
    start_marker: str,
    end_marker: str,
    new_block: str,
) -> bool:
    """Replace text enclosed by *start_marker* and *end_marker*."""
    content = _read(path)
    start = content.find(start_marker)
    if start == -1:
        return False
    end = content.find(end_marker, start + len(start_marker))
    if end == -1:
        return False
    end += len(end_marker)

    replacement = (
        content[:start]
        + start_marker
        + '\n'
        + new_block
        + '\n'
        + end_marker
        + content[end:]
    )

    if replacement != content:
        _write(path, replacement)
        return True
    return False


def replace_regex(
    path: str | Path,
    pattern: str,
    repl: str,
    *,
    count: int = 0,
    flags: int = re.MULTILINE,
) -> bool:
    """Regex-based replacement; returns True on any substitution."""
    content = _read(path)
    new_content, num_subs = re.subn(pattern, repl, content, count=count, flags=flags)
    if num_subs and new_content != content:
        _write(path, new_content)
        return True
    return False


def ensure_line(path: str | Path, line: str) -> bool:
    """Ensure *line* (without newline) exists somewhere in the file."""
    content = _read(path)
    if line in content:
        return False
    if not content.endswith('\n'):
        content += '\n'
    _write(path, content + line + '\n')
    return True
