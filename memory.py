from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, List, Dict


class Memory:
    """Simple JSONL-based memory for the agent.

    Each call to .append() writes a line-delimited JSON record.
    .load() returns the list of most recent records (default 50).
    """

    def __init__(self, path: Path | str = "memory.jsonl", max_retained: int = 50):
        self.path = Path(path)
        self.max_retained = max_retained
        self.path.touch(exist_ok=True)

    def append(self, data: dict[str, Any]) -> None:
        data = {**data, "ts": datetime.utcnow().isoformat() + "Z"}
        with self.path.open("a", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")

    def load(self, n: int | None = None) -> list[dict[str, Any]]:
        n = n or self.max_retained
        try:
            with self.path.open("r", encoding="utf-8") as f:
                lines = f.readlines()[-n:]
            return [json.loads(l) for l in lines]
        except Exception:
            return []
