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


def append_note(note: str):
    """Append free-form, timestamped notes created by the agent.

    This is intended for longer-term planning or thoughts the agent would like
    to persist across iterations.  They are stored in the `notes` list in
    memory.json so they can be surfaced in future prompts.
    """
    mem = load_memory()
    mem.setdefault("notes", []).append({
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "content": note,
    })
    save_memory(mem)
