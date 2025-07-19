from pathlib import Path
import tempfile, shutil, textwrap

ROOT = Path(__file__).resolve().parent

# --- Helper: safely rewrite a file ------------------------------------------------
def _rewrite(path: Path, new_content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_content, encoding="utf-8")
    tmp.replace(path)


# === Patch coder.py ==============================================================
coder_path = ROOT / "coder.py"
coder_src = coder_path.read_text(encoding="utf-8").splitlines()

def _ensure_imports(lines: list[str]) -> None:
    """Add any missing imports we need (shutil, tempfile)."""
    insert_at = None
    for idx, line in enumerate(lines):
        if line.startswith("from pathlib"):
            insert_at = idx + 1
            break
    if insert_at is None:
        return
    imports_needed = {"shutil": False, "tempfile": False}
    for line in lines:
        for imp in imports_needed:
            if f"import {imp}" in line or f"from {imp}" in line:
                imports_needed[imp] = True
    to_insert = []
    if not imports_needed["shutil"]:
        to_insert.append("import shutil")
    if not imports_needed["tempfile"]:
        to_insert.append("import tempfile")
    lines[insert_at:insert_at] = to_insert

def _inject_create_backup(lines: list[str]) -> None:
    """Insert _create_backup helper if it doesn't already exist."""
    if any("def _create_backup" in ln for ln in lines):
        return
    # find position after _restore_backup definition
    marker = None
    for idx, line in enumerate(lines):
        if line.startswith("def _restore_backup"):
            marker = idx
            break
    if marker is None:
        return
    helper_code = textwrap.dedent("""
        def _create_backup() -> Path:
            \"\"\"Copy all .py files (excluding virtual envs) into a temp dir and return its Path.\"\"\"
            backup_root = Path(tempfile.mkdtemp(prefix="code_backup_", dir=_ROOT))
            for p in _ROOT.rglob("*.py"):
                if any(x in p.parts for x in ("venv", ".venv")):
                    continue
                dest = backup_root / p.relative_to(_ROOT)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)
            return backup_root
    """).strip("\n").splitlines()
    lines[marker:marker] = [""] + helper_code + [""]

def _patch_apply_task(lines: list[str]) -> None:
    """Add backup/restore logic & static syntax check to apply_task."""
    in_func = False
    indent = " " * 4
    new_lines = []
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if line.startswith("def apply_task("):
            in_func = True
        if in_func and stripped.startswith("messages = ["):
            # Insert backup creation just before messages
            new_lines.append(indent + "backup_dir = _create_backup()")
        new_lines.append(line)
        if in_func and stripped.startswith("reply = chat_completion"):
            pass  # keep
        # Replace try/except block start to integrate syntax check & restore
        if in_func and stripped.startswith("try:") and " _safe_exec" in lines[idx + 1]:
            # Delete following lines until except to rebuild
            continue
    # Rebuild function manually may be easier
    # Instead, we will perform a simpler patch after entire load:

_patch_apply_task_done = False
def patch_apply(lines: list[str]) -> list[str]:
    out = []
    in_apply = False
    indent = " " * 4
    for i, ln in enumerate(lines):
        if ln.startswith("def apply_task("):
            in_apply = True
        if in_apply and ln.strip().startswith("status = \"ok\""):
            # we are just before try:
            out.append(ln)
            out.append(indent + "try:")
            out.append(indent * 2 + "_safe_exec(reply)")
            out.append(indent * 2 + "if not _run_static_syntax_check():")
            out.append(indent * 3 + "raise RuntimeError('Static syntax check failed after applying code.')")
            out.append(indent + "except Exception as e:")
            out.append(indent * 2 + "_restore_backup(backup_dir)")
            out.append(indent * 2 + "status = f\"error: {e}\"")
            out.append(indent * 2 + "traceback.print_exc()")
            # Skip original try/except block in source
            # Need to skip until we reach 'except' then consume until after exception handling
            # We'll scan ahead
            j = i + 1
            depth = 0
            while j < len(lines):
                l2 = lines[j]
                if l2.strip().startswith("try:"):
                    depth += 1
                if l2.strip().startswith("except"):
                    if depth == 0:
                        # skip this 'except' and following two lines (status assign and traceback)
                        j += 3
                        break
                    else:
                        depth -= 1
                j += 1
            # continue iteration from j
            i = j - 1
            in_apply = False  # We finished custom block
        else:
            out.append(ln)
    return out

_ensure_imports(coder_src)
_inject_create_backup(coder_src)
# More surgical patch: We'll rebuild apply_task entirely simpler
coder_code = "\n".join(coder_src)
# Overwrite entire apply_task definition with a safe template
import re, datetime as _dt

apply_pattern = re.compile(r"def apply_task\([^\n]+?\n(    .*\n)+?", re.MULTILINE)
def build_apply():
    indent = " " * 4
    return textwrap.dedent(f"""
    def apply_task(task: str, model: str = "o3-ver1") -> str:
        \"\"\"Use an LLM to generate Python code that fulfils `task` and execute it.

        Creates a temporary backup of the codebase; if execution or subsequent
        static syntax checks fail, the backup is automatically restored.
        Returns a short status string.
        \"\"\"
        backup_dir = _create_backup()

        messages = [
            {{
                "role": "system",
                "content": (
                    "You are a coding agent operating inside an existing repo.\\n"
                    "Given a task description, output ONLY executable Python code (no markdown)\\n"
                    "that edits files in the repository to accomplish the task.\\n"
                    "You may use standard library only.\\n"
                ),
            }},
            {{
                "role": "user",
                "content": f"Task: {{task}}\\n\\nCodebase snapshot:\\n{{_snapshot_codebase()}}",
            }},
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
            status = f"error: {{e}}"
            traceback.print_exc()

        # Log outcome
        log = _ROOT / "coder.log"
        with log.open("a", encoding="utf-8") as fp:
            fp.write(f"{{_dt.datetime.utcnow().isoformat()}} | {{task}} -> {{status}}\\n")
        return status
    """).strip("\n")
new_coder = apply_pattern.sub(build_apply(), coder_code, count=1)
# Insert _create_backup if not present (already done)
if "def _create_backup" not in new_coder:
    idx_restore = new_coder.index("def _restore_backup")
    insert_point = new_coder.find("\n", idx_restore) + 1
    new_coder = new_coder[:insert_point] + textwrap.dedent("""
def _create_backup() -> Path:
    \"\"\"Copy all .py files (excluding virtual envs) into a temp dir and return its Path.\"\"\"
    backup_root = Path(tempfile.mkdtemp(prefix="code_backup_", dir=_ROOT))
    for p in _ROOT.rglob("*.py"):
        if any(x in p.parts for x in ("venv", ".venv")):
            continue
        dest = backup_root / p.relative_to(_ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
    return backup_root

""") + new_coder[insert_point:]

_rewrite(coder_path, new_coder)

# === Patch fallback.py ==========================================================
fallback_path = ROOT / "fallback.py"
if fallback_path.exists():
    fb_lines = fallback_path.read_text(encoding="utf-8").splitlines()
    # Ensure the read_codebase function is properly closed and syntactically valid
    new_fb_lines = []
    in_function = False
    for ln in fb_lines:
        new_fb_lines.append(ln)
        if ln.strip().startswith("except UnicodeDecodeError"):
            # We expect the next lines may be missing; ensure they exist
            indent = " " * 12  # level inside for -> try -> except
            new_fb_lines.append(indent + "# Skip binary-ish files")
            new_fb_lines.append(indent + "continue")
    # Ensure function returns
    if not any(l.strip().startswith("return files") for l in new_fb_lines):
        new_fb_lines.append("    return files")
    # Add a simple __main__ guard for quick manual testing
    if not any(l.startswith("if __name__ == \"__main__\"") for l in new_fb_lines):
        new_fb_lines.extend([
            "",
            "if __name__ == \"__main__\":",
            "    root = Path(__file__).parent",
            "    print(f\"Indexed {len(read_codebase(root))} files from {root}\")",
        ])
    _rewrite(fallback_path, "\n".join(new_fb_lines))