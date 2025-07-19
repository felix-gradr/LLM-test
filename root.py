
"""Entry-point for SelfCoder orchestration.

Runs planner and executor agents every iteration.
Falls back to fallback.agent_step on any failure, with full error logging.
"""
from pathlib import Path
from error_logger import log_error

def main() -> None:
    project_root = Path(__file__).parent.resolve()
    try:
        from agents import planner_agent, executor_agent
        planner_agent.run(project_root)
        executor_agent.run(project_root)
    except Exception as exc:
        # If anything goes wrong, log and trigger fallback
        log_error("orchestrator main() failure", exc)
        try:
            from fallback import agent_step
            agent_step(project_root, model="o3-ver1")
        except Exception as fb_exc:
            log_error("fallback after orchestrator failure", fb_exc)
            raise

# Remove seed marker after first run
seed_marker = Path(__file__).parent / "seed.txt"
if seed_marker.exists():
    try:
        seed_marker.unlink()
    except Exception as e:
        log_error("root.py: failed to remove seed.txt", e)

if __name__ == "__main__":
    main()
