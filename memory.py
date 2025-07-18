from __future__ import annotations

"""Light-weight persistent memory for SelfCoder.

The goal of this module is to provide a *very simple* key-value memory that
survives across iterations.  The implementation is intentionally minimal for
now and can be expanded later (vector stores, embeddings, summaries, …).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class Memory:
    """A JSON-file backed memory store.

    The file is created on first use.  The public API is intentionally tiny – we
    only need what *root.py* currently uses.  More helpers can be added later
    without touching the call-site.
    """

    DEFAULT_STRUCTURE: Dict[str, Any] = {
        "iteration": 0,
        "consecutive_no_op": 0,
        "history": [],  # List[{timestamp, reply, action}]
    }

    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, Any] = {}
        self._load()

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def increment_iteration(self) -> None:
        self.data["iteration"] = self.data.get("iteration", 0) + 1

    def record_reply(self, reply: str, action: str) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "action": action,
            "reply": reply[:2_000],  # Truncate to keep the file small
        }
        self.data.setdefault("history", []).append(entry)
        # Keep the last 50 replies only – prevents unbounded growth
        self.data["history"] = self.data["history"][-50:]

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                # Corrupted file – start fresh but keep a backup
                backup = self.path.with_suffix(".bak")
                self.path.replace(backup)
                self.data = self.DEFAULT_STRUCTURE.copy()
        else:
            self.data = self.DEFAULT_STRUCTURE.copy()
