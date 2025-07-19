
"""logging_handler.py
Auto-installed module that routes all standard `logging` records
into error_logger.log_message(), so they are preserved in
error_log.txt *and* memory.jsonl for downstream agents.
"""

import logging
from typing import Optional

try:
    # Local import – avoids circulars if error_logger imports logging_handler
    from error_logger import log_message
except Exception as import_exc:  # pragma: no cover
    # Fallback: ensure at least something is shown
    def log_message(msg: str, *_args, **_kwargs) -> None:  # type: ignore
        print("LOGGING_HANDLER_FALLBACK:", msg, import_exc)

class MemoryLogHandler(logging.Handler):
    """Custom handler that forwards log records to error_logger."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            msg = self.format(record)
            log_message(f"[{record.levelname}] {msg}")
        except Exception as e:  # pragma: no cover
            # Last-ditch effort to avoid infinite recursion
            print("MemoryLogHandler internal failure:", e, flush=True)

_INITIALISED = False

def initialise(level: Optional[int] = logging.INFO) -> None:
    """Attach MemoryLogHandler to the root logger (idempotent)."""
    global _INITIALISED
    if _INITIALISED:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Prevent duplicate handlers across hot-reloads or multiple imports
    if not any(isinstance(h, MemoryLogHandler) for h in root_logger.handlers):
        handler = MemoryLogHandler()
        handler.setFormatter(
            logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(handler)

    _INITIALISED = True


# Initialise immediately on import so a single `import logging_handler`
# anywhere in the codebase wires up the bridge.
initialise()

# -------------------------------------------------------------------
# Auto-generated augmentation: guarantee ForwardHandler is mounted on
# the root logger as soon as this module is imported. This makes sure
# every logging call anywhere in the codebase reaches error_logger.
# -------------------------------------------------------------------
import logging

_logging_handler_attached = False

def _auto_attach_root_handler() -> None:
    """Attach ForwardHandler to root logger exactly once."""
    global _logging_handler_attached
    if _logging_handler_attached:
        return

    root_logger = logging.getLogger()
    # Avoid duplicate ForwardHandler instances.
    if not any(h.__class__.__name__ == "ForwardHandler" for h in root_logger.handlers):
        try:
            root_logger.addHandler(ForwardHandler())
            # Ensure at least INFO level so `log_message` lines are captured.
            root_logger.setLevel(min(root_logger.level, logging.INFO))
        except Exception as exc:  # pragma: no cover
            # Logging must never break the agent – swallow and report.
            print("Failed to attach ForwardHandler:", exc)

    _logging_handler_attached = True


# Auto-attach on module import
_auto_attach_root_handler()
