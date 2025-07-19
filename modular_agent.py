
"""Orchestrates Planner -> Coder -> (optional) Tester for one iteration."""

from pathlib import Path
import datetime, traceback
from planner import Planner
from coder import record_task

_ROOT = Path(__file__).parent

def run(model: str = "o3-ver1"):
    print("[MODULAR_AGENT] Planning next tasks...")
    plan = Planner(model="o4-mini").plan(n_tasks=3)
    if not plan:
        print("[MODULAR_AGENT] Planner returned no tasks.")
        return
    task = plan[0]
    print(f"[MODULAR_AGENT] Selected task: {task!r}")
    record_task(task)
    (_ROOT / "latest_plan.json").write_text(str(plan), encoding="utf-8")
    # TODO: future – invoke Coder to implement task automatically
    (_ROOT / "auto_progress.md").write_text(
        f"Planned task on {datetime.datetime.utcnow().isoformat()}: {task}",
        encoding="utf-8",
    )

if __name__ == "__main__":
    run()
