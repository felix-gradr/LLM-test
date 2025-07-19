
"""Coder component – given a task description, generate code changes.

For now, this is a stub that records the task to `pending_tasks.md`.
Future iterations will expand this into actual code-editing logic.
"""
from pathlib import Path, datetime as _dt

_ROOT = Path(__file__).parent

def record_task(task: str):
    ts = _dt.datetime.utcnow().isoformat()
    f = _ROOT / "pending_tasks.md"
    with f.open("a", encoding="utf-8") as fp:
        fp.write(f"- [{ts}] {task}\n")
    return f

if __name__ == "__main__":
    import sys
    record_task(" ".join(sys.argv[1:]) if len(sys.argv) > 1 else "demo task")
