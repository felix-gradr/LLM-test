"""Robust fallback agent – guarantees forward progress and cleans junk."""
from __future__ import annotations
from pathlib import Path
import datetime, shutil, os, traceback

def _cleanup_junk(root: Path) -> dict[str, int]:
    """Recursively delete __pycache__ dirs and *.pyc/pyo files.
    Returns a summary dict useful for diagnostics."""
    removed_dirs = 0
    removed_files = 0
    for p in root.rglob("*"):
        try:
            if p.is_dir() and p.name == "__pycache__":
                shutil.rmtree(p, ignore_errors=True)
                removed_dirs += 1
            elif p.is_file() and p.suffix in {".pyc", ".pyo"}:
                p.unlink(missing_ok=True)
                removed_files += 1
        except Exception:
            # Never raise – fallback must never break the run
            traceback.print_exc()
    return {"dirs": removed_dirs, "files": removed_files}


def _write_progress(message: str) -> None:
    ts = datetime.datetime.utcnow().isoformat()
    line = f"UTC {ts} | fallback: {message}\n"
    path = Path("auto_progress.md")
    # Append rather than overwrite (main agent may have already written)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        # Last-resort: make sure at least one line is written
        Path("auto_progress.md").write_text(line, encoding="utf-8")


def agent_step(project_root: Path, model: str = "o3-ver1") -> None:
    """Entry-point invoked by main_agent. Never raises."""
    try:
        summary = _cleanup_junk(project_root)
        _write_progress(f"cleanup_junk dirs={summary['dirs']} files={summary['files']}")
    except Exception as exc:
        # Log exception but keep going
        traceback.print_exc()
        _write_progress(f"exception: {exc}")
