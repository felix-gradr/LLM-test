"""Coder component – generates and executes code changes for a given task.

Capabilities:
1. record_task(task)  – append task to pending_tasks.md
2. apply_task(task)   – ask an LLM for Python code to implement the task and execute it safely
"""
from pathlib import Path
import difflib
import shutil
import tempfile
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

# === Safe EXEC helper (auto-inserted) ===
def _safe_exec(code: str):
    """Execute generated code with a predefined __file__ to avoid NameErrors."""
    env = {
        "__name__": "__coder_exec__",
        "__file__": str(_ROOT / "generated_exec.py"),
    }
    exec(code, env)



def _create_backup() -> Path:
    """Copy all .py files (excluding virtual envs) into a temp dir and return its Path."""
    backup_root = Path(tempfile.mkdtemp(prefix="code_backup_", dir=_ROOT))
    for p in _ROOT.rglob("*.py"):
        if any(x in p.parts for x in ("venv", ".venv")):
            continue
        dest = backup_root / p.relative_to(_ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
    return backup_root


def _write_change_diff(backup_dir: Path) -> None:
    """Write unified diff between backup_dir and current codebase to change_diffs."""
    diff_dir = _ROOT / "change_diffs"
    diff_dir.mkdir(exist_ok=True)
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    diff_path = diff_dir / f"{ts}.diff"
    parts = []
    for p in _ROOT.rglob("*.py"):
        if any(x in p.parts for x in ("venv", ".venv")):
            continue
        rel = p.relative_to(_ROOT)
        old_file = backup_dir / rel
        new_file = p
        if not old_file.exists():
            old_text = []
        else:
            old_text = old_file.read_text(encoding="utf-8").splitlines()
        new_text = new_file.read_text(encoding="utf-8").splitlines()
        if old_text == new_text:
            continue
        diff = difflib.unified_diff(
            old_text,
            new_text,
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm=""
        )
        parts.extend(list(diff))
    if parts:
        diff_path.write_text("\n".join(parts), encoding="utf-8")

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

    Creates a temporary backup of the codebase; if execution or subsequent
    static syntax checks fail, the backup is automatically restored.
    Returns a short status string.
    """
    backup_dir = _create_backup()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a coding agent operating inside an existing repo.
"
                "Given a task description, output ONLY executable Python code (no markdown)
"
                "that edits files in the repository to accomplish the task.
"
                "You may use standard library only.
"
            ),
        },
        {
            "role": "user",
            "content": f"Task: {task}

Codebase snapshot:
{_snapshot_codebase()}",
        },
    ]
    reply = chat_completion(messages, preferred_model=model)
    # Persist reply for audit
    gen_file = _ROOT / "generated_coder_reply.py"
    gen_file.write_text(reply, encoding="utf-8")

    status = "ok"
    try:
        _safe_exec(reply)
        if not _run_static_syntax_check():
            raise RuntimeError("Static syntax check failed after code execution.")
    except Exception as e:
        _restore_backup(backup_dir)
        status = f"error: {e}"
        traceback.print_exc()

    # Log outcome
    log = _ROOT / "coder.log"
    with log.open("a", encoding="utf-8") as fp:
        fp.write(f"{_dt.datetime.utcnow().isoformat()} | {task} -> {status}
")
    if status == 'ok':
        _write_change_diff(backup_dir)
    return status
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
        _safe_exec(reply)
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