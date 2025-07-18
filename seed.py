from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(override=True)

# File types that the agent is allowed to read/write.  Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md"}

# Directories we purposely ignore to keep the prompt small.
IGNORE_DIRS = {".venv", "venv", "__pycache__"}

# Load SYSTEM_PROMPT from prompt.txt
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8").strip()

# Load goal from goal.md
GOAL = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()

# ----------------------------------------------------------------------------
# Simple persistent "memory" file.  The content is injected into the prompt so
# that future iterations can recall past reasoning, decisions, and plans even
# though the model's context window is reset each step.
# ----------------------------------------------------------------------------
MEMORY_PATH = Path(__file__).parent / "memory.md"
if MEMORY_PATH.exists():
    MEMORY_CONTENT = MEMORY_PATH.read_text(encoding="utf-8").strip()
else:
    MEMORY_CONTENT = ""  # First run – no memory yet.


def read_codebase(root: Path) -> dict[str, str]:
    """Return a dict mapping relative paths to file contents, excluding large/irrelevant dirs."""
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        # Skip ignored directories early for performance
        if any(segment in IGNORE_DIRS for segment in path.parts):
            continue
        if path.suffix in CODE_EXTENSIONS and path.is_file():
            try:
                files[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
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


def agent_step(root: Path, model: str = "o3") -> None:
    global GOAL
    """Run one reasoning / coding cycle."""
    snapshot = read_codebase(root)
    # Truncate to avoid blowing past context limits
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:12000]

    # Include at most the first 4000 characters of memory to stay within budget
    memory_snippet = MEMORY_CONTENT[:4000]

    user_prompt = (
        f"Today is {datetime.utcnow().date()}.\n"
        f"Your GOAL: {GOAL}\n\n"
        f"Memory (truncated):\n{memory_snippet}\n\n"
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
    elif action == "human_help":
        print("[AGENT] Requests human assistance:\n" + actions.get("message_to_human", ""))
    elif action == "no_op":
        print("[AGENT] No changes proposed this iteration.")
    else:
        print(f"[WARN] Unknown action '{action}'. Skipping.")


def main():
    project_root = Path(__file__).parent.resolve()
    agent_step(project_root, model="o3-ver1")


if __name__ == "__main__":
    main()
