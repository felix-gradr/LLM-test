from __future__ import annotations
import traceback
from pathlib import Path
from datetime import datetime, timezone

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def log_error(context: str, exc: Exception) -> None:
    """Append a timestamped traceback to logs/error.log"""
    ts = datetime.now(timezone.utc).isoformat()
    log_path = LOG_DIR / "error.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{ts} | {context} | {repr(exc)}\n")
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
        f.write("""\n---\n""")
