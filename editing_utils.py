from __future__ import annotations
from pathlib import Path
import difflib
import textwrap


def replace_between_markers(
    file_path: str | Path,
    start_marker: str,
    end_marker: str,
    new_block: str,
) -> None:
    """Replace text between two (unique) marker lines inclusively."""
    p = Path(file_path)
    original = p.read_text(encoding="utf-8").splitlines()
    try:
        i_start = original.index(start_marker)
        i_end = original.index(end_marker)
    except ValueError as e:
        raise RuntimeError(f"Markers not found in {file_path}: {e}")
    updated = original[: i_start + 1] + textwrap.dedent(new_block).splitlines() + original[i_end:]
    p.write_text("\n".join(updated), encoding="utf-8")


def show_diff(old: str, new: str) -> str:
    """Return unified diff between two strings (for logging/display)."""
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), fromfile="old", tofile="new", lineterm=""
        )
    )
