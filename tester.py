
"""Tester component – execute quick sanity checks after each iteration.

Current implementation:
  1. Ensures `python -m root` does not crash (dry run via subprocess).
  2. TODO: Add unit tests for utilities.
"""
from pathlib import Path, subprocess, sys, datetime as _dt

_ROOT = Path(__file__).parent

def smoke_test():
    log = _ROOT / "tester.log"
    ts = _dt.datetime.utcnow().isoformat()
    try:
        result = subprocess.run([sys.executable, "-m", "root"], cwd=_ROOT, capture_output=True, text=True, timeout=60)
        status = "OK" if result.returncode == 0 else f"FAIL ({result.returncode})"
    except Exception as e:
        status = f"ERROR {e}"
    log.write_text(f"{ts}: {status}\n", encoding="utf-8")
    return status

if __name__ == "__main__":
    print(smoke_test())
