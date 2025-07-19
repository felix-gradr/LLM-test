from pathlib import Path
import textwrap
import re

ROOT = Path(__file__).parent

# 1. Create / update error_logger.py
error_logger_path = ROOT / "error_logger.py"
error_logger_code = textwrap.dedent("""
    \"\"\"Primitive repo-wide error logging utility.

    Importing this module installs a sys.excepthook that logs uncaught exceptions
    to error.log at the repository root.  Can also be used manually via
    log_exception().
    \"\"\"
    from __future__ import annotations
    import sys
    import traceback
    import datetime as _dt
    from pathlib import Path

    _ROOT = Path(__file__).parent
    _LOG_FILE = _ROOT / "error.log"

    def _write(msg: str) -> None:
        try:
            with _LOG_FILE.open("a", encoding="utf-8") as fp:
                fp.write(msg)
        except Exception:
            # as a last resort, emit to stderr
            sys.stderr.write(msg)

    def _excepthook(exc_type, exc_value, exc_tb):
        ts = _dt.datetime.utcnow().isoformat()
        header = f"[{ts}] {exc_type.__name__}: {exc_value}\\n"
        _write(header)
        # Capture traceback
        tb_lines = traceback.format_tb(exc_tb)
        _write(''.join(tb_lines))
        # Delegate to default hook for visibility
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    # Install only once
    if not getattr(sys, "_error_logger_installed", False):
        sys.excepthook = _excepthook
        sys._error_logger_installed = True

    def log_exception(exc: BaseException) -> None:
        \"\"\"Manually log an exception inside an except block.\"\"\"
        _excepthook(type(exc), exc, exc.__traceback__)
    """).lstrip()
error_logger_path.write_text(error_logger_code, encoding="utf-8")

def ensure_import(file_path: Path):
    code = file_path.read_text(encoding="utf-8")
    if "import error_logger" in code:
        return
    lines = code.splitlines()
    # Find last future import or first import block line
    insert_idx = 0
    for i, ln in enumerate(lines):
        if re.match(r"from __future__ import", ln):
            insert_idx = i + 1
        elif ln.strip().startswith(("import ", "from ")):
            insert_idx = max(insert_idx, i + 1)
        elif ln.strip() and not ln.startswith("#"):
            # first non-import code line
            break
    lines.insert(insert_idx, "import error_logger  # Auto-imported for global error logging")
    file_path.write_text("\n".join(lines), encoding="utf-8")

# 2. Patch coder.py and fallback.py to import error_logger
ensure_import(ROOT / "coder.py")
ensure_import(ROOT / "fallback.py")