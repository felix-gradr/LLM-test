"""
seed_agent.py – minimal self‑coding agent seed

Requirements:
    • Python ≥ 3.10
    • openai ≥ 1.0

Setup:
    1.  pip install -U openai
    2.  export OPENAI_API_KEY="sk‑..."  # or set OPENAI_API_KEY in PowerShell

Usage example (PowerShell):
    python seed_agent.py --goal "Build infrastructure that lets you plan and extend yourself safely" --iterations 3

This script gives an LLM read/write access to its own source tree so it can plan
and iteratively extend itself.  The agent emits structured JSON instructions
that are applied to the local codebase.  If it needs help from a human it will
raise the **human_help** action with a message.

⚠️  SECURITY & ETHICS  ⚠️
—————————————————————
Running self‑modifying agents is risky.  Keep them sandboxed, version‑controlled
(Git), and subject to human review.  Do **not** point them at sensitive files or
production environments without strong safeguards.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import openai

# File types that the agent is allowed to read/write.  Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md"}

# System instruction for the LLM.
SYSTEM_PROMPT = """You are **SelfCoder**, an autonomous coding agent.
You can read and modify files in this repository to achieve the long‑term **GOAL**
provided by the user.  Think step‑by‑step and plan tooling before tackling the
final objective.

If you need the human to perform something outside your sandbox (e.g. installing
packages), return the action `human_help` with clear instructions.

When you finish an iteration, reply with **only** valid JSON, following exactly
this schema:
{
  "action": "modify_files | create_files | append_files | human_help | no_op",
  "changes": [  // required for file actions, omitted otherwise
    { "path": "relative/path.py", "content": "<FULL NEW FILE CONTENT>" }
  ],
  "message_to_human": "<optional>"  // required for human_help
}
Do **not** output anything except JSON.
"""


def read_codebase(root: Path) -> dict[str, str]:
    """Return a dict mapping relative paths to file contents."""
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.suffix in CODE_EXTENSIONS and path.is_file():
            try:
                files[str(path.relative_to(root))] = path.read_text()
            except UnicodeDecodeError:
                # Skip binary or non‑UTF8 files
                continue
    return files


def apply_changes(root: Path, changes: list[dict]):
    """Write files returned by the LLM safely inside *root*."""
    for change in changes:
        rel_path = change["path"].lstrip("/\\")
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change["content"], encoding="utf‑8")
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Wrote {rel_path}")


def agent_step(goal: str, root: Path, model: str = "gpt-4o-mini") -> None:
    """Run one reasoning / coding cycle."""
    snapshot = read_codebase(root)
    # Truncate to avoid blowing past context limits
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:12000]

    user_prompt = (
        f"Today is {datetime.utcnow().date()}.\n"
        f"Your GOAL: {goal}\n\n"
        f"Here is the current codebase (truncated):\n{joined}"
    )

    response = openai.ChatCompletion.create(
        model=model,
        temperature=0.2,
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
    parser = argparse.ArgumentParser("Self‑coding agent seed")
    parser.add_argument("--goal", required=True, help="High‑level goal for the agent")
    parser.add_argument("--iterations", type=int, default=1, help="How many cycles to run")
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.resolve()
    for i in range(args.iterations):
        print(f"\n=== Iteration {i + 1}/{args.iterations} ===")
        agent_step(args.goal, project_root, args.model)


if __name__ == "__main__":
    main()
