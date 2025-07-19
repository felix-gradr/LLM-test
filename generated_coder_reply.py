from pathlib import Path
import re
import textwrap
import tempfile
import shutil

ROOT = Path(__file__).parent


def _ensure_imports(source: str) -> str:
    """Ensure required safety imports exist in coder.py source."""
    imports_needed = {"tempfile", "shutil"}
    existing_imports = set(re.findall(r"^\s*import (\w+)", source, flags=re.MULTILINE))
    missing = imports_needed - existing_imports
    if missing:
        first_import = re.search(r"^\s*import [\w, ]+", source, flags=re.MULTILINE)
        if first_import:
            insert_at = first_import.end()
            before = source[:insert_at]
            after = source[insert_at:]
            for imp in sorted(missing):
                before += f"\nimport {imp}"
            return before + after
    return source


def _build_new_apply_task() -> str:
    """Return the new, safer apply_task() implementation."""
    return textwrap.dedent(
        '''
        def apply_task(task: str, model: str = "o3-ver1") -> str:
            """Use an LLM to generate Python code that fulfills `task` and execute it safely.
    
            The function now:
            1. Creates a backup of all .py files before execution.
            2. Executes the generated code.
            3. Runs a static syntax check across the repo.
            4. Restores from backup if the syntax check fails.
            """
            import traceback, uuid
            backup_dir = Path(tempfile.mkdtemp(prefix="code_backup_"))
            # --- Step 1: snapshot current .py files ---
            for p in _ROOT.rglob("*.py"):
                if backup_dir in p.parents:
                    continue
                rel = p.relative_to(_ROOT)
                dest = backup_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(p, dest)
                except Exception:
                    # Non-critical; continue copying others
                    continue
    
            # --- Step 2: ask LLM for code changes ---
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
    
            status = "ok"
            try:
                exec(reply, {"__name__": "__coder_exec__"})
            except Exception as e:
                status = f"error during exec: {e}"
                traceback.print_exc()
    
            # --- Step 3: static syntax check ---
            if not _run_static_syntax_check():
                # --- Step 4: restore backup on failure ---
                _restore_backup(backup_dir)
                status = "reverted: static check failed"
    
            # Clean up backup directory
            try:
                shutil.rmtree(backup_dir)
            except Exception:
                pass
    
            # Log outcome
            log = _ROOT / "coder.log"
            with log.open("a", encoding="utf-8") as fp:
                import datetime as _dt
                fp.write(f"{_dt.datetime.utcnow().isoformat()} | {task} -> {status}\\n")
            return status
        '''
    )


def patch_coder_py() -> None:
    coder_path = ROOT / "coder.py"
    source = coder_path.read_text(encoding="utf-8")

    # Ensure imports for tempfile and shutil
    source = _ensure_imports(source)

    # Replace existing apply_task definition
    new_apply_task = _build_new_apply_task()
    pattern = re.compile(
        r"def apply_task\(.+?^\s*return [^\n]+", re.DOTALL | re.MULTILINE
    )
    source, n = pattern.subn(new_apply_task, source)
    if n == 0:
        # Fallback if pattern not found; append the new function
        source += "\n\n" + new_apply_task

    coder_path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    patch_coder_py()