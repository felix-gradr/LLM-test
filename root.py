"""Entry-point for SelfCoder.

On failure, falls back to fallback.agent_step, but now records
all errors using error_logger.log_error so future iterations
can inspect them.
"""
from pathlib import Path
from error_logger import log_error
from datetime import datetime, timezone

def main() -> None:
    try:
        ### Main agent logic placeholder ###
        # Currently unimplemented; deliberately raise to trigger fallback
        raise NotImplementedError("Main agent not implemented yet")
    except Exception as exc:
        # Log error details before invoking fallback agent
        log_error("root.py main() failure", exc)
        # Invoke fallback
        try:
            from fallback import agent_step
            project_root = Path(__file__).parent.resolve()
            agent_step(project_root, model="o3-ver1")
        except Exception as fallback_exc:
            # Even fallback failed; record this too
            log_error("fallback.agent_step() failure", fallback_exc)
            # Re-raise so that external runners notice hard failure
            raise


# Ensure the 'seed.txt' marker is removed after first run for clarity
seed_marker = Path(__file__).parent / "seed.txt"
if seed_marker.exists():
    try:
        seed_marker.unlink()
    except Exception as e:
        log_error("root.py: failed to remove seed.txt", e)
if __name__ == "__main__":
    main()
