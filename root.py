from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from openai import AzureOpenAI

from memory import Memory

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Configuration & constants
# ---------------------------------------------------------------------------
CODE_EXTENSIONS = {".py", ".txt", ".md"}  # Expand later if needed
CONTEXT_WINDOW = 12_000  # ~12k characters of code + prompt per request
LOOP_NO_OP_LIMIT = 3  # How many consecutive no-ops are considered a loop

# System prompt and immutable goal
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8").strip()
GOAL = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def read_codebase(root: Path) -> Dict[str, str]:
    """Return a mapping of *relative* file paths to their UTF-8 contents."""
    files: Dict[str, str] = {}
    for path in root.rglob("*"):
        if path.suffix in CODE_EXTENSIONS and path.is_file():
            try:
                files[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Skip non-UTF-8 or binary files
                continue
    return files


def apply_changes(root: Path, changes: list[dict[str, Any]]):
    """Write file *changes* safely inside *root* directory."""
    for change in changes:
        rel_path = change["path"].lstrip("/\\")
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change["content"], encoding="utf-8")
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Wrote {rel_path}")


# ---------------------------------------------------------------------------
# Core agent loop
# ---------------------------------------------------------------------------

def agent_step(project_root: Path, model: str = "o3-ver1") -> None:
    """Execute one reasoning / coding iteration."""

    # --------------------------------------------------
    # 1. Persistent memory
    # --------------------------------------------------
    memory_file = project_root / "memory.json"
    memory = Memory(memory_file)

    # Basic loop protection – if we got stuck in no-op loop, ask for human help
    if memory.data.get("consecutive_no_op", 0) >= LOOP_NO_OP_LIMIT:
        print("[LOOP-PROTECT] Detected potential stall – requesting human assistance.")
        memory.increment_iteration()
        memory.record_reply("<auto-detected-loop>", "human_help")
        memory.save()
        print("[AGENT] Please provide new high-level guidance or reset memory.json to continue.")
        return

    # --------------------------------------------------
    # 2. Build user prompt (code snapshot + memory snippet)
    # --------------------------------------------------
    snapshot = read_codebase(project_root)
    joined_code = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:CONTEXT_WINDOW]

    memory_snippet = json.dumps(memory.data, indent=2)[:2_000]

    user_prompt = (
        f"Today is {datetime.utcnow().date()}.\n"
        f"Your GOAL: {GOAL}\n\n"
        f"Here is the current codebase (truncated):\n{joined_code}\n\n"
        f"Memory (truncated):\n{memory_snippet}"
    )

    # --------------------------------------------------
    # 3. Call the LLM
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 4. Parse & act on reply
    # --------------------------------------------------
    try:
        actions = json.loads(reply)
    except json.JSONDecodeError:
        print("[WARN] LLM returned invalid JSON. Skipping iteration.")
        return

    action = actions.get("action")

    if action in {"modify_files", "create_files", "append_files"}:
        apply_changes(project_root, actions.get("changes", []))
    elif action == "human_help":
        print("[AGENT] Requests human assistance:\n" + actions.get("message_to_human", ""))
    elif action == "no_op":
        print("[AGENT] No changes proposed this iteration.")
    else:
        print(f"[WARN] Unknown action '{action}'. Skipping.")

    # --------------------------------------------------
    # 5. Update memory & housekeeping
    # --------------------------------------------------
    memory.increment_iteration()
    memory.record_reply(reply, action)
    if action == "no_op":
        memory.data["consecutive_no_op"] = memory.data.get("consecutive_no_op", 0) + 1
    else:
        memory.data["consecutive_no_op"] = 0
    memory.save()

    # Delete seed.txt (only on first run)
    seed_file = project_root / "seed.txt"
    if seed_file.exists():
        seed_file.unlink()
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Deleted {seed_file}")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main():
    project_root = Path(__file__).parent.resolve()
    agent_step(project_root, model="o3-ver1")


if __name__ == "__main__":
    main()
