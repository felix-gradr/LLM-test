"""Entry point for SelfCoder.

Workflow:
1. Try the main agent (`main_agent.run()`).
2. If that fails, fall back to `fallback.agent_step()` **only** if Azure
   credentials are configured.
3. Regardless of outcome, append a timestamp to progress.log so the project
   never appears stuck.
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

def _update_iteration_report() -> None:
    """Append a human-readable summary of the latest plan to iteration_report.md.

    This is a lightweight form of change history that helps humans trace
    progress across iterations without digging into progress.log.
    """
    report = Path(__file__).parent / "iteration_report.md"
    plan_file = Path(__file__).parent / "latest_plan.json"
    ts = datetime.now(timezone.utc).isoformat()
    try:
        import json as _json
        tasks = _json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.is_file() else []
    except Exception:
        tasks = []
    with report.open("a", encoding="utf-8") as fp:
        fp.write(f"\n### {ts}\n")
        if tasks:
            for t in tasks:
                fp.write(f"- {t}\n")
        else:
            fp.write("- (no plan for this iteration)\n")

from importlib import import_module
from types import ModuleType
from typing import Optional


def _log_progress(label: str = "root") -> None:
    progress_file = Path(__file__).parent / "progress.log"
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    with progress_file.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} – {label} completed\n")


def _env_has_azure_credentials() -> bool:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    return bool(os.getenv("AZURE_KEY") and os.getenv("AZURE_ENDPOINT"))


def _safe_import(name: str) -> Optional[ModuleType]:
    try:
        return import_module(name)
    except Exception as exc:
        print(f"[WARN] Could not import {name}: {exc}")
        return None


def _run_main_agent() -> None:
    agent = _safe_import("main_agent")
    if agent and hasattr(agent, "run"):
        agent.run()  # Let exceptions propagate to outer try
        _log_progress("main_agent")
        return
    raise RuntimeError("main_agent unavailable or missing run()")  # pragma: no cover


def _run_fallback(project_root: Path) -> None:
    if not _env_has_azure_credentials():
        print("[INFO] Azure credentials missing; skipping fallback agent.")
        return
    fb = _safe_import("fallback")
    if fb and hasattr(fb, "agent_step"):
        fb.agent_step(project_root, model="o3-ver1")
        _log_progress("fallback_agent")
    else:
        print("[ERROR] fallback module or agent_step missing.")


def main() -> None:
    project_root = Path(__file__).parent.resolve()

    try:
        _run_main_agent()
    except Exception as exc:
        print(f"[WARN] main agent error: {exc}. Switching to fallback.")
        _run_fallback(project_root)

    # Always ensure some progress is logged
    _log_progress("root")
    _update_iteration_report()


if __name__ == "__main__":
    main()

    # Remove seed.txt after first successful run
    seed_file = Path(__file__).parent / "seed.txt"
    if seed_file.is_file():
        seed_file.unlink()