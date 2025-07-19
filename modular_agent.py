"""Orchestrates Planner → Coder for one iteration.

Workflow:
    1. Planner proposes several tasks.
    2. Select the highest-priority task.
    3. Coder attempts to implement it automatically.
"""
from pathlib import Path
import datetime, traceback
from planner import Planner
from coder import record_task, apply_task

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

    # Save full plan for visibility
    (_ROOT / "latest_plan.json").write_text(
        json.dumps(plan, indent=2), encoding="utf-8"
    )

    # Attempt to apply the task
    try:
        status = apply_task(task, model=model)
    except Exception as exc:
        status = f"exception: {exc}"
        traceback.print_exc()

    # Always write auto_progress to demonstrate forward movement
    (_ROOT / "auto_progress.md").write_text(
        f"UTC {datetime.datetime.utcnow().isoformat()} | task: {task} | status: {status}\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    run()