from pathlib import Path
import datetime as _dt, traceback, difflib

# === Existing imports remain ===
from llm_utils import chat_completion

# Rest of original coder.py up to _ROOT definition stays unchanged
# We will append / inject new helpers and enhance existing functions below.


# ------------------------------------------------------------
# NEW: Executed-tasks tracking & diff logging helpers
# ------------------------------------------------------------
_EXECUTED = Path(__file__).parent / "executed_tasks.md"
_DIFF_DIR = Path(__file__).parent / "change_diffs"
_DIFF_DIR.mkdir(exist_ok=True)

def _has_executed(task: str) -> bool:
    """Return True if the exact task string has already been executed."""
    if not _EXECUTED.is_file():
        return False
    try:
        existing = _EXECUTED.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    return any(t.split("] ", 1)[-1] == task for t in existing if "] " in t)

def _mark_executed(task: str):
    """Append task to executed_tasks.md with timestamp."""
    ts = _dt.datetime.utcnow().isoformat()
    with _EXECUTED.open("a", encoding="utf-8") as fp:
        fp.write(f"- [{ts}] {task}\n")

def _dict_code_snapshot() -> dict[str, str]:
    """Return mapping of relative .py file paths -> contents (utf-8)."""
    root = Path(__file__).parent
    snap = {}
    for p in root.rglob("*.py"):
        if any(x in p.parts for x in ("venv", ".venv")):
            continue
        try:
            snap[str(p.relative_to(root))] = p.read_text(encoding="utf-8")
        except Exception:
            continue
    return snap

def _write_diff(before: dict[str, str], after: dict[str, str], task: str):
    """Compute unified diff between before and after snapshots and persist."""
    ts = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    diff_lines = []
    all_keys = set(before) | set(after)
    for key in sorted(all_keys):
        pre = before.get(key, "").splitlines(keepends=True)
        post = after.get(key, "").splitlines(keepends=True)
        if pre == post:
            continue
        diff_lines.extend(difflib.unified_diff(
            pre, post,
            fromfile=f"a/{key}",
            tofile=f"b/{key}",
            lineterm=""
        ))
        diff_lines.append("")  # newline separator
    if not diff_lines:
        return  # nothing changed
    diff_path = _DIFF_DIR / f"{ts}.diff"
    header = f"# Task: {task}\n# Timestamp: {ts} UTC\n\n"
    diff_path.write_text(header + "\n".join(diff_lines), encoding="utf-8")

# ------------------------------------------------------------
# PATCH: enhance apply_task
# ------------------------------------------------------------
def apply_task(task: str, model: str = "o3-ver1") -> str:
    """Use an LLM to generate Python code that fulfils `task` and execute it.

    Returns a short status string.
    """
    # Skip if task already executed
    if _has_executed(task):
        return "skipped: already executed"

    before_snap = _dict_code_snapshot()  # snapshot before any change

    messages = [
        {
            "role": "system",
            "content": (
                "You are a coding agent operating inside an existing repo.\n"
                "Given a task description, output ONLY executable Python code (no markdown)\n"
                "that edits files in the repository to accomplish the task.\n"
                "You may use standard library only.\n"
            ),
        },
        {
            "role": "user",
            "content": f"Task: {task}\n\nCodebase snapshot:\n{_snapshot_codebase()}",
        },
    ]
    reply = chat_completion(messages, preferred_model=model)
    # Persist reply for audit
    gen_file = _ROOT / "generated_coder_reply.py"
    gen_file.write_text(reply, encoding="utf-8")

    status = "ok"
    try:
        _safe_exec(reply)
    except Exception as e:
        status = f"error: {e}"
        traceback.print_exc()

    # Snapshot after execution & write diff if no error
    after_snap = _dict_code_snapshot()
    if status == "ok":
        _write_diff(before_snap, after_snap, task)
        _mark_executed(task)

    # Log outcome
    log = _ROOT / "coder.log"
    with log.open("a", encoding="utf-8") as fp:
        fp.write(f"{_dt.datetime.utcnow().isoformat()} | {task} -> {status}\n")
    return status

# Note: record_task and other existing code remain unchanged.