
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

MEMORY_FILE = Path(__file__).parent / "memory.jsonl"
MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB cap to avoid uncontrolled growth


def _ensure_file() -> None:
    if not MEMORY_FILE.exists():
        MEMORY_FILE.touch()


def add_memory(content: str, meta: Dict[str, Any] | None = None) -> None:
    """
    Append a memory entry to disk. Keeps file size under the cap by trimming
    oldest entries if needed.
    """
    _ensure_file()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "content": content,
        "meta": meta or {},
    }
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Trim if necessary
    if MEMORY_FILE.stat().st_size > MAX_SIZE_BYTES:
        lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()
        # keep last 70%
        keep_from = int(len(lines) * 0.3)
        MEMORY_FILE.write_text("\n".join(lines[keep_from:]), encoding="utf-8")


def load_memories(limit: int | None = 50) -> List[Dict[str, Any]]:
    _ensure_file()
    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()
    items = [json.loads(l) for l in lines if l.strip()]
    if limit is not None:
        items = items[-limit:]
    return items
