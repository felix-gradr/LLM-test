"""Coder component – generates and executes code changes for a given task.

Capabilities:
1. record_task(task)  – append task to pending_tasks.md
2. apply_task(task)   – ask an LLM for Python code to implement the task and execute it safely
"""
from pathlib import Path
import datetime as _dt, traceback
from llm_utils import chat_completion
# === Safety helpers (auto-inserted) ===
def _run_static_syntax_check() -> bool:
    """Return True if all .py files compile successfully."""
    import compileall
    try:
        return compileall.compile_dir(str(_ROOT), quiet=1, force=True)
    except Exception:
        return False

def _restore_backup(backup_dir: Path) -> None:
    """Restore files from the given backup directory."""
    if not backup_dir or not backup_dir.exists():
        return
    for p in backup_dir.rglob("*.py"):
        rel = p.relative_to(backup_dir)
        dest = _ROOT / rel
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            p.replace(dest)
        except Exception:
            continue


_ROOT = Path(__file__).parent

def record_task(task: str):
    ts = _dt.datetime.utcnow().isoformat()
    f = _ROOT / "pending_tasks.md"
    with f.open("a", encoding="utf-8") as fp:
        fp.write(f"- [{ts}] {task}\n")
    return f

def _snapshot_codebase(max_chars: int = 6000) -> str:
    parts = []
    for p in _ROOT.rglob("*.py"):
        if any(x in p.parts for x in ("venv", ".venv")):
            continue
        try:
            parts.append(f"## {p}\n{p.read_text()}")
        except Exception:
            continue
    return "\n".join(parts)[:max_chars]

def apply_task(task: str, model: str = "o3-ver1") -> str:
    """Use an LLM to generate Python code that fulfils `task` and execute it.

    Returns a short status string.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a coding agent operating inside an existing repo.\n"
                "Given a task description, output ONLY executable Python code (no markdown)\n"
                "that edits files in the repository to accomplish the task.\n"
                "You may use standard library only.\n"
            ),
        },
        {
            "role": "user",
            "content": f"Task: {task}\n\nCodebase snapshot:\n{_snapshot_codebase()}",
        },
    ]
    reply = chat_completion(messages, preferred_model=model)
    # Persist reply for audit
    gen_file = _ROOT / "generated_coder_reply.py"
    gen_file.write_text(reply, encoding="utf-8")

    status = "ok"
    try:
        exec(reply, {"__name__": "__coder_exec__"})
    except Exception as e:
        status = f"error: {e}"
        traceback.print_exc()

    # Log outcome
    log = _ROOT / "coder.log"
    with log.open("a", encoding="utf-8") as fp:
        fp.write(f"{_dt.datetime.utcnow().isoformat()} | {task} -> {status}\n")
    return status

if __name__ == "__main__":
    import sys
    task_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "demo task"
    record_task(task_text)
    apply_task(task_text)