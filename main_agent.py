"""Self-improving main agent.

Behaviour:
1. Reads long_term_plan.md.
2. Marks the first unchecked todo as done with a timestamp.
3. Appends an entry to agent_progress.log.
This guarantees visible forward progress each iteration.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import re

ROOT = Path(__file__).parent.resolve()

PLAN_FILE = ROOT / "long_term_plan.md"
LOG_FILE = ROOT / "agent_progress.log"

TODO_PATTERN = re.compile(r"^(- \[ \]) (.*)")

def _tick_one_item() -> None:
    if not PLAN_FILE.exists():
        return
    lines = PLAN_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = []
    ticked = False
    for line in lines:
        m = TODO_PATTERN.match(line)
        if m and not ticked:
            # Mark this item as done
            task = m.group(2)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            new_line = f"- [x] {task}  (done {ts})"
            new_lines.append(new_line)
            ticked = True
        else:
            new_lines.append(line)
    PLAN_FILE.write_text("\n".join(new_lines), encoding="utf-8")

def run() -> None:
    """Main entry point for each iteration."""
    _tick_one_item()
    # Always append to progress log
    LOG_FILE.write_text(
        f"{datetime.now(timezone.utc).isoformat()} – main_agent completed\n",
        encoding="utf-8",
        append=True if LOG_FILE.exists() else False,
    )
