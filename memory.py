"""Thread-safe JSONL memory store.

Fixes:
    1. Ensures the file is always created before use.
    2. Guarantees writes are flushed & fsynced (prevents data-loss on crash).
    3. Adds a mutex to prevent race-conditions in concurrent writes.
    4. Safely trims the file when it exceeds MAX_FILE_SIZE.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constants
_ROOT = Path(__file__).resolve().parent
MEMORY_FILE = _ROOT / "memory.jsonl"
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _ensure_file() -> None:
    """Make sure memory.jsonl exists."""
    if not MEMORY_FILE.exists():
        MEMORY_FILE.touch()


def _trim_if_oversize() -> None:
    """Trim the oldest half of the file if it grows beyond MAX_FILE_SIZE."""
    if MEMORY_FILE.stat().st_size <= MAX_FILE_SIZE:
        return

    with MEMORY_FILE.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    # Keep only the newest half
    keep_from = len(lines) // 2
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        f.writelines(lines[keep_from:])


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def add_memory(data: Dict[str, Any]) -> None:
    """Append a single JSON entry to the memory file in a thread-safe way."""
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        **data,
    }

    _ensure_file()
    serialised = json.dumps(record, ensure_ascii=False)

    with _LOCK:
        with MEMORY_FILE.open("a", encoding="utf-8") as f:
            f.write(serialised + "\n")
            f.flush()
            os.fsync(f.fileno())
        _trim_if_oversize()


def log_error(error: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """Shortcut to log an error event to the memory."""
    add_memory(
        {
            "type": "error",
            "error": error,
            "meta": meta or {},
        }
    )


def load_memories() -> List[Dict[str, Any]]:
    """Load all memory entries, skipping corrupted lines."""
    _ensure_file()
    memories: List[Dict[str, Any]] = []

    with _LOCK:
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    memories.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines to avoid crashing the whole loader
                    continue
    return memories
