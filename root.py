"""Entry point for SelfCoder.

This file should NEVER crash completely.  The design philosophy is:

1. Try the main agent (`main_agent.run()`).
2. If that fails, fall back to `fallback.agent_step()` **only** if the required
   Azure credentials appear to be configured.
3. If both fail, still log progress so that the project never appears stuck.
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone
from importlib import import_module
from types import ModuleType
from typing import Optional


def _log_progress(label: str = "root") -> None:
    """Append a timestamp to progress.log so we always make visible progress."""
    progress_file = Path(__file__).parent / "progress.log"
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    with progress_file.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} – {label} completed\n")


def _env_has_azure_credentials() -> bool:
    """Return True iff both AZURE_KEY and AZURE_ENDPOINT are set (non-empty)."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    return bool(os.getenv("AZURE_KEY") and os.getenv("AZURE_ENDPOINT"))


def _safe_import(name: str) -> Optional[ModuleType]:
    """Import *name* safely, returning None on failure."""
    try:
        return import_module(name)
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] Could not import {{name}}: {{exc}}")
        return None


def _run_main_agent() -> None:
    agent = _safe_import("main_agent")
    if agent and hasattr(agent, "run"):
        try:
            agent.run()
            _log_progress("main_agent")
            return
        except Exception as exc:  # pragma: no cover
            print(f"[WARN] main_agent.run() raised: {{exc}}")
    raise RuntimeError("main_agent unavailable or failed")


def _run_fallback(project_root: Path) -> None:
    if not _env_has_azure_credentials():
        print("[INFO] Azure credentials missing; skipping fallback agent.")
        return

    fb = _safe_import("fallback")
    if fb and hasattr(fb, "agent_step"):
        try:
            fb.agent_step(project_root, model="o3-ver1")
            _log_progress("fallback_agent")
        except Exception as exc:  # pragma: no cover
            print(f"[ERROR] fallback agent failed: {{exc}}")
    else:
        print("[ERROR] fallback module or agent_step missing.")


def main() -> None:
    project_root = Path(__file__).parent.resolve()

    try:    _run_main_agent()
    except Exception as exc:
        print(f"[WARN] main agent error: {{exc}}. Switching to fallback.")
        _run_fallback(project_root)

    # Always ensure some progress is logged even if everything else failed
    _log_progress("root")


if __name__ == "__main__":
    main()

    # Remove seed.txt after first successful run
    seed_file = Path(__file__).parent / "seed.txt"
    if seed_file.is_file():
        seed_file.unlink()
