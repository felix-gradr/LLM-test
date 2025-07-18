from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(override=True)

# File types that the agent is allowed to read/write.  Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md"}

# Load SYSTEM_PROMPT from prompt.txt
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8").strip()

# Load goal from goal.md
GOAL = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()


def read_codebase(root: Path) -> dict[str, str]:
    """Return a dict mapping relative paths to file contents."""
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.suffix in CODE_EXTENSIONS and path.is_file():
            try:
                files[str(path.relative_to(root))] = path.read_text()
            except UnicodeDecodeError:
                # Skip binary or non-UTF8 files
                continue
    return files


def apply_changes(root: Path, changes: list[dict]):
    """Write files returned by the LLM safely inside *root*."""
    for change in changes:
        rel_path = change["path"].lstrip("/\\")
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change["content"], encoding="utf-8")
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Wrote {rel_path}")


def _run_pytest_if_available(project_root: Path) -> Optional[int]:
    """Run pytest if it is installed and return the exit code. None if pytest unavailable."""
    try:
        import importlib.util

        if importlib.util.find_spec("pytest") is None:
            return None
    except Exception:
        # Any unexpected issue while checking for pytest – skip running tests.
        return None

    print("[TEST] Running pytest suite …")
    result = subprocess.run([
        sys.executable,
        "-m",
        "pytest",
        "-q",
    ], cwd=project_root)

    if result.returncode == 0:
        print("[TEST] ✔ All tests passed.")
    else:
        print("[TEST] ✖ Tests failed. Exit code:", result.returncode)
    return result.returncode


def agent_step(root: Path, model: str = "o3") -> None:
    global GOAL
    """Run one reasoning / coding cycle."""
    snapshot = read_codebase(root)
    # Truncate to avoid blowing past context limits
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:12000]

    user_prompt = (
        f"Today is {datetime.utcnow().date()}.\n"
        f"Your GOAL: {GOAL}\n\n"
        f"Here is the current codebase (truncated):\n{joined}"
    )

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_KEY"),
        azure_endpoint=os.getenv("AZURE_ENDPOINT"),
        api_version="2025-03-01-preview",
    )

    response = client.chat.completions.create(
        model=model,
        reasoning_effort="high",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    reply = response.choices[0].message.content.strip()
    try:
        actions = json.loads(reply)
    except json.JSONDecodeError:
        print("[WARN] LLM returned invalid JSON. Skipping iteration.")
        return

    action = actions.get("action")
    if action in {"modify_files", "create_files", "append_files"}:
        apply_changes(root, actions.get("changes", []))

        # After applying code changes, immediately run the test-suite if available
        _run_pytest_if_available(root)

    elif action == "human_help":
        print("[AGENT] Requests human assistance:\n" + actions.get("message_to_human", ""))
    elif action == "no_op":
        print("[AGENT] No changes proposed this iteration.")
    else:
        print(f"[WARN] Unknown action '{action}'. Skipping.")

    # Delete seed.txt (only relevant for the first run)
    seed_file = root / "seed.txt"
    if seed_file.exists():
        seed_file.unlink()
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Deleted {seed_file}")


def main():
    project_root = Path(__file__).parent.resolve()
    agent_step(project_root, model="o3-ver1")


if __name__ == "__main__":
    main()
