
"""Centralised error logging.

Persists errors to:
1. A persistent plain-text file (error_log.txt) for easy human access.
2. The JSONL memory store via memory.add_memory so next iterations can
   reason about past failures.
"""
from __future__ import annotations

import datetime
import traceback
from pathlib import Path
from typing import Any, Optional

from memory import add_memory  # type: ignore


LOG_PATH = Path(__file__).parent / "error_log.txt"


def _utcnow_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def log_error(exc: BaseException, context: Optional[str] = None, **extras: Any) -> None:
    """Persist an exception + context.

    Args:
        exc: The exception instance.
        context: Optional free-text context string.
        **extras: Any serialisable extra information to store.
    """
    timestamp = _utcnow_iso()
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    record = {
        "type": "error",
        "timestamp": timestamp,
        "context": context or "",
        "traceback": tb,
        **extras,
    }

    # 1. Append to text file for humans
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(f"{'-'*80}\n{timestamp}\n")
        if context:
            fh.write(f"Context: {context}\n")
        fh.write(tb)
        fh.write("\n")

    # 2. Store in memory for future agent reasoning
    add_memory(record)
