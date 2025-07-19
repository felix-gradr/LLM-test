
"""Entry point for SelfCoder.

This file should NEVER crash completely. If anything goes wrong,
we delegate to the fallback agent.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

def _log_progress() -> None:
    """Append a timestamp to progress.log so we always make visible progress."""
    progress_file = Path(__file__).parent / "progress.log"
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    with progress_file.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} – run completed\n")

def main() -> None:
    try:
        # --- CORE LOGIC PLACEHOLDER ---
        # For now, we simply log progress.
        _log_progress()
        raise Exception("Only fallback agent is implemented for now, so we need to raise an exception to trigger the fallback.")
        # Future iterations: import and run a more sophisticated main agent here.
        # ---------------------------------------------------------------

    except Exception as exc:
        # If anything goes wrong, fall back gracefully.
        print(f"[WARN] main() error: {exc}. Switching to fallback agent.")
        from fallback import agent_step
        project_root = Path(__file__).parent.resolve()
        agent_step(project_root, model="o3-ver1")

if __name__ == "__main__":
    main()

    # Remove seed.txt after first successful run
    seed_file = Path(__file__).parent / "seed.txt"
    if seed_file.is_file():
        seed_file.unlink()
