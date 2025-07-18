from __future__ import annotations

"""Structured memory utilities for SelfCoder.

This module centralises memory handling so that other parts of the codebase
can benefit from higher-level operations (appending typed entries, searching,
summarising, etc.).  It is **deliberately** independent from the core loop so
that root.py does not need to change right away – we can integrate gradually
& safely.

Rationale
---------
The existing implementation in *root.py* stores plain text lines in
``memory.log``.  That works, but it is difficult to query or build features
(like long-term planning, searching for past mistakes, detecting infinite
loops ...).  The structured JSONL format introduced here remains completely
append-only and therefore safe, yet it unlocks richer capabilities.

Design goals
============
1. **Backward compatible** – the legacy *memory.log* is left untouched for
   now so nothing breaks.
2. **Append-only** – we never rewrite history.
3. **Low risk** – no external dependencies; pure stdlib.

Typical usage
-------------
>>> from memory_manager import Memory
>>> Memory.append('reflection', 'I should avoid repeating the same bug')
>>> last = Memory.load(last_n=3)
>>> excerpt = Memory.summarise(max_chars=4000)
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Literal, List, Dict

# ---------------------------------------------------------------------------
# Public, easy-to-use façade
# ---------------------------------------------------------------------------

EntryType = Literal[
    "plan",       # long-term planning or next-steps
    "action",     # changes applied in an iteration
    "observation",# world or codebase observations
    "reflection", # meta level thoughts / lessons learned
]


class Memory:
    """Namespace-style utility class (static methods only)."""

    # Location of the new structured memory file.
    _PATH: Path = Path(__file__).parent / "memory.jsonl"
    # Safety cap: avoid loading a gigantic file into RAM during summarisation.
    _SUMMARY_CHAR_LIMIT: int = 8000  # ~2k tokens

    # -------------------------- Low-level helpers --------------------------
    @staticmethod
    def _timestamp() -> str:
        """Return an ISO8601 timestamp in UTC, truncated to seconds."""
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    # -------------------------- Public helpers ----------------------------
    @staticmethod
    def append(entry_type: EntryType, content: str) -> None:
        """Append a typed entry to *memory.jsonl* (one JSON per line)."""
        Memory._PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": Memory._timestamp(),
            "type": entry_type,
            "content": content.strip(),
        }
        with Memory._PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def load(last_n: int | None = None) -> List[Dict]:
        """Return the last *n* records (or all if *None*).

        The order is preserved (old->new).
        """
        if not Memory._PATH.is_file():
            return []
        with Memory._PATH.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        if last_n is not None:
            lines = lines[-last_n:]
        return [json.loads(ln) for ln in lines]

    @staticmethod
    def summarise(max_chars: int | None = None) -> str:
        """Return a *plain text* excerpt of the most recent records.

        Concatenates the *content* fields in chronological order until
        *max_chars* (default: internal limit) is reached.  This is intended to
        be fed back into the LLM as the MEMORY excerpt.
        """
        max_chars = max_chars or Memory._SUMMARY_CHAR_LIMIT
        records = Memory.load()
        excerpt_parts: List[str] = []
        # Start from the end (newest) but build the excerpt reversed later.
        current_len = 0
        for rec in reversed(records):
            text = f"[{rec['ts']}] ({rec['type']}) {rec['content']}"
            new_len = current_len + len(text) + 1  # +1 for newline
            if new_len > max_chars:
                break
            excerpt_parts.append(text)
            current_len = new_len
        # We iterated backwards, so restore chronological order.
        excerpt = "\n".join(reversed(excerpt_parts))
        return excerpt
