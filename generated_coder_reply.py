from pathlib import Path
import sys
import textwrap
import datetime as _dt
import traceback
import os
import threading


def _upsert(path: Path, content: str, marker: str | None = None) -> None:
    """
    Create or update `path` with `content`.
    If `marker` is supplied and already present in the existing file, do nothing.
    """
    if path.exists() and marker and marker in path.read_text(encoding="utf-8"):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_sitecustomize(repo_root: Path) -> None:
    """
    1)  Install sitecustomize.py that:
        • installs a global excepthook that logs traceback to root_crash.log
        • hooks threading.excepthook (≥3.8) to do the same
        • enforces Python ≥3.8
    """
    marker = "# AUTO-GENERATED STARTUP HARDENING"
    sitecustomize = repo_root / "sitecustomize.py"

    content = textwrap.dedent(
        f"""
        {marker}
        \"\"\"
        Automatically generated to harden startup and ensure failures never go silent.
        This module is imported automatically at interpreter start-up (via `site`).
        \"\"\"

        import sys, os, traceback, datetime as _dt, threading

        LOG_FILE = os.environ.get("ROOT_CRASH_LOG", "root_crash.log")

        def _log_unhandled(etype, value, tb):
            ts = _dt.datetime.utcnow().isoformat()
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as fp:
                    fp.write(f"{{ts}}\\n")
                    traceback.print_exception(etype, value, tb, file=fp)
                    fp.write("=" * 80 + "\\n")
            except Exception:
                # If logging fails we still want the default behaviour
                pass
            # Continue with the default hook so the traceback appears on stderr
            sys.__excepthook__(etype, value, tb)

        if not getattr(sys, "__root_excepthook_installed__", False):
            sys.excepthook = _log_unhandled
            sys.__root_excepthook_installed__ = True

            # Capture background-thread exceptions (Python ≥ 3.8)
            if hasattr(threading, "excepthook"):
                _orig_threading_hook = threading.excepthook  # type: ignore[attr-defined]

                def _threading_hook(args):
                    _log_unhandled(args.exc_type, args.exc_value, args.exc_traceback)
                    _orig_threading_hook(args)

                threading.excepthook = _threading_hook  # type: ignore[attr-defined]

        # Enforce minimum Python version
        if sys.version_info < (3, 8):
            sys.stderr.write(
                f"Python {{sys.version.split()[0]}} is too old. "
                "Python ≥ 3.8 is required.\\n"
            )
            sys.exit(1)
        """
    ).lstrip()

    _upsert(sitecustomize, content, marker)


def _guard_root_main(root_pkg: Path) -> None:
    """
    2)  Prepend a guard to root/__main__.py so that any exception inside the module
        is logged to root_crash.log before propagating.
    """
    main_file = root_pkg / "__main__.py"
    if not main_file.exists():
        return

    guard_marker = "# STARTUP_GUARD_INSTALLED"
    if guard_marker in main_file.read_text(encoding="utf-8"):
        return

    guard_code = textwrap.dedent(
        f"""
        {guard_marker}
        import sys, traceback, datetime as _dt, os

        _ROOT_CRASH_LOG = os.environ.get("ROOT_CRASH_LOG", "root_crash.log")

        def _log_and_reraise():
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type is None:
                return
            ts = _dt.datetime.utcnow().isoformat()
            try:
                with open(_ROOT_CRASH_LOG, "a", encoding="utf-8") as f:
                    f.write(f"{{ts}} | Unhandled in root.__main__\\n")
                    traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
                    f.write("=" * 80 + "\\n")
            except Exception:
                pass

        def _wrap_main(func):
            def _inner(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except SystemExit:
                    raise
                except Exception:
                    _log_and_reraise()
                    raise
            return _inner

        # If a main() callable exists, wrap it.
        if "main" in globals() and callable(globals()["main"]):
            globals()["main"] = _wrap_main(globals()["main"])
        """
    ).lstrip()

    original = main_file.read_text(encoding="utf-8")
    _upsert(main_file, guard_code + "\n" + original)


def main() -> None:
    repo_root = Path(__file__).resolve().parent

    # Task 1 & 2: Install sitecustomize and guard root/__main__.py
    _create_sitecustomize(repo_root)

    root_pkg = repo_root / "root"
    if root_pkg.is_dir():
        _guard_root_main(root_pkg)


if __name__ == "__main__":
    main()