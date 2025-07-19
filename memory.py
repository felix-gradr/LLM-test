import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

MEMORY_PATH = Path(__file__).parent / "memory.json"

def load_memory() -> Dict[str, Any]:
    if MEMORY_PATH.is_file():
        try:
            return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_memory(payload: Dict[str, Any]):
    MEMORY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def add_event(event: str):
    """Append a timestamped event string to memory.json under the key `events`."""
    mem = load_memory()
    mem.setdefault("events", []).append({
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "event": event,
    })
    save_memory(mem)


def append_note(note: Any):
    """Append free-form, timestamped notes created by the agent.

    Accepts any JSON-serialisable Python object (str, dict, list, ...).  The
    value is stored under the key `content` so it can be arbitrary.  This
    relaxation allows the agent to persist richer context (e.g. structured
    plans) instead of being limited to plain strings.
    """
    mem = load_memory()
    mem.setdefault("notes", []).append({
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "content": note,
    })
    save_memory(mem)
