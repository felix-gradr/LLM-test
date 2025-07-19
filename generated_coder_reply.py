from pathlib import Path
import textwrap

def _replace_cleanup_function(file_path: Path):
    src_lines = file_path.read_text().splitlines(keepends=True)

    # Locate the start of the _cleanup_junk function
    start_idx = None
    for i, line in enumerate(src_lines):
        if line.lstrip().startswith("def _cleanup_junk"):
            start_idx = i
            break
    if start_idx is None:
        return  # Function not found; nothing to do

    # Locate the end of the function (next top-level statement or EOF)
    end_idx = len(src_lines)
    for j in range(start_idx + 1, len(src_lines)):
        stripped = src_lines[j].lstrip()
        if stripped and not src_lines[j].startswith((" ", "\t")):
            end_idx = j
            break

    # New enhanced _cleanup_junk implementation
    new_func = textwrap.dedent(
        """
        def _cleanup_junk() -> None:
            \"\"\"Remove transient files and trim logs to keep the repo tidy.

            1. Delete one-time seed.txt (if present)
            2. Trim coder.log to the last 300 lines
            3. Rotate generated_coder_reply.py into generated_backups/ (keep 3 most recent)
            4. Recursively delete __pycache__ directories and .pyc files
            \"\"\"
            import time, shutil

            root = _ROOT

            # (1) Remove seed.txt on first run
            seed = root / "seed.txt"
            if seed.exists():
                try:
                    seed.unlink()
                except Exception:
                    pass

            # (2) Trim coder.log
            log = root / "coder.log"
            if log.exists():
                try:
                    lines = log.read_text(encoding="utf-8", errors="ignore").splitlines()
                    max_lines = 300
                    if len(lines) > max_lines:
                        log.write_text("\\n".join(lines[-max_lines:]), encoding="utf-8")
                except Exception:
                    pass

            # (3) Rotate generated_coder_reply.py
            gen = root / "generated_coder_reply.py"
            if gen.exists():
                try:
                    backup_dir = root / "generated_backups"
                    backup_dir.mkdir(exist_ok=True)
                    ts = int(time.time())
                    gen.replace(backup_dir / f"coder_reply_{ts}.py")
                    backups = sorted(
                        backup_dir.glob("coder_reply_*.py"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                    for p in backups[3:]:
                        try:
                            p.unlink()
                        except Exception:
                            pass
                except Exception:
                    pass

            # (4) Delete .pyc files and __pycache__ directories
            try:
                for p in root.rglob("*"):
                    if p.is_dir() and p.name == "__pycache__":
                        try:
                            shutil.rmtree(p)
                        except Exception:
                            pass
                    elif p.is_file() and p.suffix == ".pyc":
                        try:
                            p.unlink()
                        except Exception:
                            pass
            except Exception:
                pass

        """
    ).lstrip("\n")

    # Replace old function with new
    new_src = "".join(src_lines[:start_idx]) + new_func + "".join(src_lines[end_idx:])
    file_path.write_text(new_src, encoding="utf-8")


if __name__ == "__main__":
    coder_file = Path(__file__).parent / "coder.py"
    _replace_cleanup_function(coder_file)