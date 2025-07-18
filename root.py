from __future__ import annotations

import json
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

from openai import AzureOpenAI

# --- NEW ---------------------------------------------------------------
# Prefer the new structured memory manager but keep legacy log for
# backward-compatibility & easy grepping.  This staged approach minimises
# risk while we port existing features.
try:
    from memory_manager import Memory  # type: ignore
except Exception as exc:  # pragma: no cover – should never fail
    Memory = None  # fallback handled later
    print("[WARN] Failed to import memory_manager –", exc)

# Loop-protection (may be absent on very first run)
try:
    from loop_protection import LoopProtector  # type: ignore
except Exception as exc:  # pragma: no cover
    LoopProtector = None
    print("[WARN] Failed to import loop_protection –", exc)
# ----------------------------------------------------------------------

load_dotenv(override=True)

# File types that the agent is allowed to read/write.  Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md"}

# Legacy flat-text memory file (kept for now).
MEMORY_PATH = Path(__file__).parent / "memory.log"
MEMORY_CHAR_LIMIT = 4000  # ~ 1k tokens

# Load SYSTEM_PROMPT from prompt.txt
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8").strip()

# Load goal from goal.md
GOAL = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Helper functions – filesystem & .gitignore handling (unchanged)
# ---------------------------------------------------------------------------


[...UNCHANGED CONTENT OF ROOT.PY UNTIL THE POINT JUST AFTER json.loads(reply)...]

    try:
        actions = json.loads(reply)
    except json.JSONDecodeError:
        print("[WARN] LLM returned invalid JSON. Skipping iteration.")
        return

    # ------------------------------------------------------------------
    # Loop-protection: skip if the exact same payload was seen last time
    # ------------------------------------------------------------------
    if LoopProtector is not None and LoopProtector.is_redundant(actions):
        print("[AGENT] Repeated identical action detected; preventing potential loop.")
        _append_memory("Skipped repeated identical action", entry_type="reflection")
        return

    action = actions.get("action")
    if action in {"modify_files", "create_files", "append_files"}:
        apply_changes(root, actions.get("changes", []))
        _append_memory(json.dumps(actions, ensure_ascii=False), entry_type="action")
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
