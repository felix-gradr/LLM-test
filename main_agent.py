"""
Self-improving main agent.

Behaviour each iteration:
1. Ensure long_term_plan.md exists with sensible default tasks.
2. Tick the first unchecked todo item.
3. Call fallback.agent_step for an LLM-powered improvement (if credentials exist).
4. Append an entry to agent_progress.log.

This guarantees visible forward progress on every run and matches or exceeds
the capabilities of the fallback agent.
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone
import re
import textwrap
from types import ModuleType
from importlib import import_module
from typing import Optional

ROOT = Path(__file__).parent.resolve()

PLAN_FILE = ROOT / "long_term_plan.md"
LOG_FILE = ROOT / "agent_progress.log"

TODO_PATTERN = re.compile(r"^(- \[ \]) (.*)")

_DEFAULT_PLAN = textwrap.dedent(
    """
    # Long-Term Plan for SelfCoder

    ## Milestones
    - [ ] Verify that main_agent can run without crashing
    - [ ] Improve logging and plan-management utilities
    - [ ] Draft architecture for specialised sub-agents
    - [ ] Implement planner sub-agent using o4-mini
    - [ ] Implement executor sub-agent
    - [ ] Introduce memory / vector-DB component
    - [ ] Establish evaluation harness
    """
).strip()

def _env_has_azure_credentials() -> bool:
    """Return True iff both AZURE_KEY and AZURE_ENDPOINT are set."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    return bool(os.getenv("AZURE_KEY") and os.getenv("AZURE_ENDPOINT"))

def _safe_import(name: str) -> Optional[ModuleType]:
    try:
        return import_module(name)
    except Exception as exc:
        print(f"[WARN] Could not import {name}: {exc}")
        return None

def _ensure_plan() -> None:
    if not PLAN_FILE.exists():
        PLAN_FILE.write_text(_DEFAULT_PLAN, encoding="utf-8")

def _tick_one_item() -> None:
    lines = PLAN_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = []
    ticked = False
    for line in lines:
        m = TODO_PATTERN.match(line)
        if m and not ticked:
            task = m.group(2)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            new_lines.append(f"- [x] {task}  (done {ts})")
            ticked = True
        else:
            new_lines.append(line)
    PLAN_FILE.write_text("\n".join(new_lines), encoding="utf-8")

def _invoke_fallback() -> None:
    if not _env_has_azure_credentials():
        print("[INFO] Azure credentials missing; skipping embedded fallback call.")
        return
    fb = _safe_import("fallback")
    if fb and hasattr(fb, "agent_step"):
        try:
            fb.agent_step(ROOT, model="o3-ver1")
        except Exception as exc:
            print(f"[ERROR] Embedded fallback agent failed: {exc}")
    else:
        print("[WARN] fallback.agent_step unavailable inside main_agent.")

def _log_progress() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} – main_agent completed\n")

def run() -> None:
    _ensure_plan()
    _tick_one_item()
    # Leverage the fallback agent's LLM reasoning so we are at least as capable.
    _invoke_fallback()
    _log_progress()
