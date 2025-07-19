from pathlib import Path
import sys, textwrap, re, io, os

ROOT = Path(__file__).parent

def ensure_error_logging_module():
    target = ROOT / "error_logging.py"
    if target.exists():
        return
    code = textwrap.dedent('''
        """Centralised error logging for all components."""
        from __future__ import annotations
        import sys, logging, traceback, threading
        from pathlib import Path

        _ROOT = Path(__file__).parent
        _LOG_FILE = _ROOT / "errors.log"

        logging.basicConfig(
            level=logging.ERROR,
            format="%(asctime)s | %(levelname)s | %(message)s",
            filename=str(_LOG_FILE),
            filemode="a",
            encoding="utf-8",
        )

        def _log_exc(exc_type, exc, tb):
            logging.error("Uncaught exception:\\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))

        # Install for main thread
        sys.excepthook = _log_exc

        # Install for any new threads (Python >=3.8)
        def _thread_hook(args):
            _log_exc(args.exc_type, args.exc_value, args.exc_traceback)
        threading.excepthook = _thread_hook
    ''').lstrip()
    target.write_text(code, encoding="utf-8")

def prepend_import(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    if "import error_logging" in content:
        return
    # Preserve shebang or from __future__ lines at the very top
    lines = content.splitlines()
    insert_idx = 0
    while insert_idx < len(lines) and (
        lines[insert_idx].startswith("#!") or
        re.match(r"from __future__ import", lines[insert_idx])
    ):
        insert_idx += 1
    lines.insert(insert_idx, "import error_logging")
    file_path.write_text("\n".join(lines), encoding="utf-8")

def main():
    ensure_error_logging_module()
    for fname in ("coder.py", "fallback.py"):
        fpath = ROOT / fname
        if fpath.is_file():
            prepend_import(fpath)

if __name__ == "__main__":
    main()