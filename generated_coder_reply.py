from pathlib import Path
import datetime as _dt, traceback, shutil, tempfile
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


def _cleanup_junk() -> None:
    """Remove transient files and trim logs to keep the repo tidy.

    1. Delete one-time seed.txt (if present)
    2. Trim coder.log to the last 300 lines
    3. Rotate generated_coder_reply.py into generated_backups/ (keep 3 most recent)
    """
    import time, shutil

    # (1) Remove seed.txt on first run
    seed = _ROOT / "seed.txt"
    if seed.exists():
        try:
            seed.unlink()
        except Exception:
            pass

    # (2) Trim coder.log
    log = _ROOT / "coder.log"
    if log.exists():
        try:
            lines = log.read_text(encoding="utf-8", errors="ignore").splitlines()
            max_lines = 300
            if len(lines) > max_lines:
                log.write_text("\n".join(lines[-max_lines:]), encoding="utf-8")
        except Exception:
            pass

    # (3) Rotate generated_coder_reply.py
    gen = _ROOT / "generated_coder_reply.py"
    if gen.exists():
        try:
            backup_dir = _ROOT / "generated_backups"
            backup_dir.mkdir(exist_ok=True)
            ts = int(time.time())
            gen.replace(backup_dir / f"coder_reply_{ts}.py")
            backups = sorted(backup_dir.glob("coder_reply_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
            for p in backups[3:]:
                try:
                    p.unlink()
                except Exception:
                    pass
        except Exception:
            pass


def _create_backup() -> Path:
    """Create a temporary backup of all .py files and return its directory path."""
    backup_root = Path(tempfile.mkdtemp(prefix="code_backup_", dir=_ROOT))
    for p in _ROOT.rglob("*.py"):
        if any(x in p.parts for x in ("venv", ".venv", "generated_backups")):
            continue
        dest = backup_root / p.relative_to(_ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(p, dest)
        except Exception:
            continue
    return backup_root


def record_task(task: str):
    ts = _dt.datetime.utcnow().isoformat()
    f = _ROOT / "pending_tasks.md"
    with f.open("a", encoding="utf-8") as fp:
        fp.write(f"- [{ts}] {task}\n")
    return f


def _snapshot_codebase(max_chars: int = 6000) -> str:
    parts = []
    for p in _ROOT.rglob("*.py"):
        if any(x in p.parts for x in ("venv", ".venv", "generated_backups")):
            continue
        if p.name in {"generated_coder_reply.py"}:
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
    # (0) Clean up any junk from previous runs BEFORE we begin
    _cleanup_junk()

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

    # Backup current codebase
    backup_dir = _create_backup()

    status = "ok"
    try:
        _safe_exec(reply)
        # After modifications, ensure everything still compiles
        if not _run_static_syntax_check():
            raise RuntimeError("Static syntax check failed after applying task.")
    except Exception as e:
        status = f"error: {e}"
        traceback.print_exc()
        # Restore from backup if something went wrong
        _restore_backup(backup_dir)

    # Remove backup directory (success or fail – it's no longer needed)
    try:
        shutil.rmtree(backup_dir, ignore_errors=True)
    except Exception:
        pass

    # Log outcome
    log = _ROOT / "coder.log"
    with log.open("a", encoding="utf-8") as fp:
        fp.write(f"{_dt.datetime.utcnow().isoformat()} | {task} -> {status}\n")

    # Final cleanup (rotate new generated_coder_reply etc.)
    _cleanup_junk()
    return status


if __name__ == "__main__":
    import sys
    task_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "demo task"
    record_task(task_text)
    apply_task(task_text)