from pathlib import Path
import re
import textwrap
import datetime as _dt
import shutil

ROOT = Path(__file__).parent
TARGET = ROOT / "coder.py"

def _replace_apply_task(src: str) -> str:
    """Replace the existing apply_task definition with a hardened version."""
    lines = src.splitlines(keepends=True)
    start_idx = None
    end_idx = None
    # Locate the start of apply_task
    for i, line in enumerate(lines):
        if line.startswith("def apply_task("):
            start_idx = i
            break
    if start_idx is None:
        return src  # nothing to do
    # Locate the end of apply_task by finding the next top-level definition or statement
    for j in range(start_idx + 1, len(lines)):
        if lines[j].strip() and not lines[j].startswith((" ", "\t")):
            end_idx = j
            break
    if end_idx is None:
        end_idx = len(lines)

    hardened_func = textwrap.dedent("""
    def apply_task(task: str, model: str = "o3-ver1") -> str:
        \"\"\"Use an LLM to generate Python code that fulfils `task` and execute it safely.

        The function now:
        1. Creates a timestamped backup of the current codebase.
        2. Executes the LLM-generated patch.
        3. Runs a static syntax check across the repo.
        4. Rolls back to the backup if execution or static check fails.

        Returns a short status string describing the outcome.
        \"\"\"
        import traceback
        from pathlib import Path as _Path
        import datetime as _dt
        import shutil as _shutil

        # === Phase 1: ask the LLM for a code patch ===
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a coding agent operating inside an existing repo.\\n"
                    "Given a task description, output ONLY executable Python code (no markdown)\\n"
                    "that edits files in the repository to accomplish the task.\\n"
                    "You may use standard library only.\\n"
                ),
            },
            {
                "role": "user",
                "content": f"Task: {task}\\n\\nCodebase snapshot:\\n{_snapshot_codebase()}",
            },
        ]
        reply = chat_completion(messages, preferred_model=model)

        # Persist reply for audit
        gen_file = _ROOT / "generated_coder_reply.py"
        gen_file.write_text(reply, encoding="utf-8")

        # === Phase 2: create a backup ===
        backup_dir = _ROOT / ".coder_backups" / _dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        for p in _ROOT.rglob("*.py"):
            if any(x in p.parts for x in ("venv", ".venv", "__pycache__")):
                continue
            dest = backup_dir / p.relative_to(_ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                dest.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            except UnicodeDecodeError:
                # Shouldn't happen for .py, but just in case
                dest.write_bytes(p.read_bytes())

        status = "ok"
        try:
            # === Phase 3: attempt to execute generated code ===
            exec(reply, {"__name__": "__coder_exec__"})
        except Exception as e:
            status = f"error_exec: {e}"
            traceback.print_exc()
            _restore_backup(backup_dir)
        else:
            # === Phase 4: static syntax check ===
            if not _run_static_syntax_check():
                status = "rollback_static_check_failed"
                _restore_backup(backup_dir)
            else:
                # Success; clean up old backup to save space
                try:
                    _shutil.rmtree(backup_dir)
                except Exception:
                    pass

        # === Phase 5: log outcome ===
        log = _ROOT / "coder.log"
        with log.open("a", encoding="utf-8") as fp:
            fp.write(f"{_dt.datetime.utcnow().isoformat()} | {task} -> {status}\\n")
        return status
    """).lstrip("\n")

    # Replace old function
    return "".join(lines[:start_idx] + [hardened_func] + lines[end_idx:])

def main() -> None:
    original = TARGET.read_text(encoding="utf-8")
    updated = _replace_apply_task(original)
    if updated != original:
        TARGET.write_text(updated, encoding="utf-8")

if __name__ == "__main__":
    main()