from pathlib import Path
import textwrap, inspect, datetime as _dt, re, sys, json, hashlib, os, shutil

ROOT = Path(__file__).parent

def _update_coder_py() -> None:
    coder_path = ROOT / "coder.py"
    original = coder_path.read_text(encoding="utf-8")

    # If we've already patched (idempotency), exit early
    if "### BEGIN AUTO-BACKUP PATCH" in original:
        return

    # We will inject a backup / rollback mechanism inside apply_task
    patched_lines = []
    inserted = False
    for line in original.splitlines():
        patched_lines.append(line)
        if not inserted and line.lstrip().startswith("def apply_task("):
            # Walk until the docstring closes to insert after it
            patched_lines.append("")  # ensure newline
            indent = " " * (len(line) - len(line.lstrip()) + 4)
            injection = textwrap.dedent(f"""
                ### BEGIN AUTO-BACKUP PATCH
                # Automatically back up all existing .py files (outside virtual envs)
                # before executing generated code.  In case of an error, the codebase
                # is rolled back to prevent leaving it in a broken state.
                import tempfile, shutil, os as _os

                _backup_dir = tempfile.mkdtemp(prefix="coder_backup_")
                _pre_existing = {{}}
                for _p in _ROOT.rglob("*.py"):
                    if any(x in _p.parts for x in ("venv", ".venv")):
                        continue
                    try:
                        rel = _p.relative_to(_ROOT)
                        dst = Path(_backup_dir) / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(_p, dst)
                        _pre_existing[rel.as_posix()] = True
                    except Exception:
                        continue

                def _rollback_from_backup():
                    \"\"\"Restore files from the backup directory and delete new files.\"\"\"
                    for _p in _ROOT.rglob("*.py"):
                        if any(x in _p.parts for x in ("venv", ".venv")):
                            continue
                        rel = _p.relative_to(_ROOT).as_posix()
                        if rel not in _pre_existing:
                            # New file created — remove it
                            try:
                                _p.unlink()
                            except Exception:
                                pass
                    # Restore originals
                    for _file in Path(_backup_dir).rglob("*.py"):
                        rel = _file.relative_to(_backup_dir)
                        target = _ROOT / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(_file, target)
                        except Exception:
                            pass
                ### END AUTO-BACKUP PATCH
            """).strip("\n")
            # Re-indent
            injection = "\n".join(indent + l if l else "" for l in injection.splitlines())
            patched_lines.append(injection)
            inserted = True

    new_content = "\n".join(patched_lines)

    # Now patch the except block that handles exec failure to add rollback
    pattern = r"except Exception as e:\s*\n\s*status = f\"error: {e}\"\s*\n\s*traceback\.print_exc\(\)"
    repl = (
        "except Exception as e:\n"
        "        status = f\"error: {e}\"\n"
        "        traceback.print_exc()\n"
        "        # <<< AUTO-BACKUP PATCH ROLLBACK >>>\n"
        "        try:\n"
        "            _rollback_from_backup()\n"
        "        except Exception as _rb_exc:\n"
        "            print('Rollback failed', _rb_exc, file=sys.stderr)"
    )
    new_content = re.sub(pattern, repl, new_content, flags=re.MULTILINE)

    coder_path.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    _update_coder_py()