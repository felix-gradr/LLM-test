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


# --------------------------------------------------------------------------------------
# HIGH-LEVEL MEMORY SUMMARY (moved from root.py)
# --------------------------------------------------------------------------------------

def summarise_memory(max_events: int = 20, max_notes: int = 10) -> str:
    """Return a concise JSON snippet with the most recent events & notes.

    Instead of dumping the entire memory file (which can grow unbounded), we
    surface only the last *max_events* and *max_notes* entries.  This keeps
    prompts small and focuses the LLM on the most relevant, recent context.
    """
    mem = load_memory()
    events = mem.get("events", [])[-max_events:]
    notes = mem.get("notes", [])[-max_notes:]
    subset = {"events": events, "notes": notes}
    try:
        return json.dumps(subset, indent=2)
    except Exception:
        # Fallback to a simple string representation if serialization fails
        return str(subset)



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


# --------------------------------------------------------------------------------------
# HIGH-LEVEL MEMORY SUMMARY (moved from root.py)
# --------------------------------------------------------------------------------------

def summarise_memory(max_events: int = 20, max_notes: int = 10) -> str:
    """Return a concise JSON snippet with the most recent events & notes.

    Instead of dumping the entire memory file (which can grow unbounded), we
    surface only the last *max_events* and *max_notes* entries.  This keeps
    prompts small and focuses the LLM on the most relevant, recent context.
    """
    mem = load_memory()
    events = mem.get("events", [])[-max_events:]
    notes = mem.get("notes", [])[-max_notes:]
    subset = {"events": events, "notes": notes}
    try:
        return json.dumps(subset, indent=2)
    except Exception:
        # Fallback to a simple string representation if serialization fails
        return str(subset)

