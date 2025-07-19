from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from memory import add_event, append_note
from openai import AzureOpenAI

load_dotenv(override=True)

# --------------------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------------------

# File types that the agent is allowed to read/write.  Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md", ".json"}

# Load SYSTEM_PROMPT from prompt.txt
SYSTEM_PROMPT = (
    Path(__file__).parent / "system_prompt.txt"
).read_text(encoding="utf-8").strip()

# Load GOAL from goal.md
GOAL = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()

# Path to persistent memory the agent can maintain across iterations
MEMORY_PATH = Path(__file__).parent / "memory.json"

# --------------------------------------------------------------------------------------
# MEMORY HELPERS
# --------------------------------------------------------------------------------------

def _load_memory() -> dict:
    """Read the persistent memory file, returning an empty dict if it does not yet exist."""
    if MEMORY_PATH.is_file():
        try:
            return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _summarise_memory(max_chars: int = 4000) -> str:
    """Return a truncated JSON representation of memory suitable for prompts."""
    mem = _load_memory()
    text = json.dumps(mem, indent=2)[:max_chars]
    return text

# --------------------------------------------------------------------------------------
# .GITIGNORE UTILS (unchanged)
# --------------------------------------------------------------------------------------

def _read_gitignore(root: Path) -> list[str]:
    """Read and parse .gitignore rules from the root directory."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []

    patterns = []
    with gitignore.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _is_ignored(path: Path, root: Path, ignore_patterns: list[str]) -> bool:
    """Check if a path is ignored by .gitignore rules."""
    import fnmatch

    rel_path = str(path.relative_to(root).as_posix())
    for pattern in ignore_patterns:
        # Handle directory-only patterns (e.g., "node_modules/")
        if pattern.endswith('/'):
            if rel_path.startswith(pattern):
                return True
            if fnmatch.fnmatch(rel_path, pattern + '*'):
                return True
        # Handle patterns without slashes (e.g., "*.log")
        elif '/' not in pattern:
            if fnmatch.fnmatch(path.name, pattern):
                return True
        # Handle patterns with slashes (e.g., "config/*.ini")
        else:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
    return False

# --------------------------------------------------------------------------------------
# FILE I/O HELPERS
# --------------------------------------------------------------------------------------

def read_codebase(root: Path) -> dict[str, str]:
    """Return a dict mapping relative paths to file contents, respecting .gitignore."""

    files: dict[str, str] = {}
    ignore_patterns = _read_gitignore(root)
    for path in root.rglob("*"):
        if path.is_dir() or _is_ignored(path, root, ignore_patterns):
            continue
        if path.suffix in CODE_EXTENSIONS and path.is_file():
            try:
                files[str(path.relative_to(root))] = path.read_text()
            except UnicodeDecodeError:
                # Skip binary / non-UTF8 files
                continue
    return files


def _apply_full_writes(root: Path, changes: list[dict]):
    """Write full-file contents to disk."""
    for change in changes:
        rel_path = change["path"].lstrip("/\\")
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change["content"], encoding="utf-8")
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Wrote {rel_path}")


def _apply_patches(root: Path, patches: list[dict]):
    """Apply in-place regex replacements to existing files.

    Each patch dict must contain:
      * path: file to modify (must already exist)
      * search: regex pattern to search for
      * replace: replacement text (can contain back-references as per re.sub)
    """
    for patch in patches:
        rel_path = patch["path"].lstrip("/\\")
        target = root / rel_path
        if not target.exists():
            print(f"[WARN] patch_files: {rel_path} does not exist, skipping.")
            continue
        content = target.read_text(encoding="utf-8")
        new_content, n = re.subn(patch["search"], patch["replace"], content, flags=re.MULTILINE)
        if n == 0:
            print(f"[WARN] patch_files: pattern not found in {rel_path}.")
        else:
            target.write_text(new_content, encoding="utf-8")
            print(
                f"[{datetime.utcnow().isoformat(timespec='seconds')}] Patched {rel_path} ({n} replacement{'s' if n!=1 else ''})"
            )

# --------------------------------------------------------------------------------------
# AGENT ORCHESTRATION
# --------------------------------------------------------------------------------------

def agent_step(root: Path, model: str = "o3-ver1") -> None:
    """Run one reasoning / coding cycle."""

    # Snapshot current code for context
    snapshot = read_codebase(root)
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:100000]

    # Add timestamp, memory & codebase to user prompt
    memory_summary = _summarise_memory()
    user_prompt = (
        f"Today is {datetime.utcnow().date()}.\n"
        f"Persistent memory (truncated):\n{memory_summary}\n\n"
        f"Here is the current codebase (truncated):\n{joined}"
    )

    # Compose system prompt with GOAL
    system_prompt_with_goal = (
        f"{SYSTEM_PROMPT}\n\n ================================== Current GOAL:\n{GOAL}"
    )

    # LLM CALL
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_KEY"),
        azure_endpoint=os.getenv("AZURE_ENDPOINT"),
        api_version="2025-03-01-preview",
    )

    response = client.chat.completions.create(
        model=model,
        reasoning_effort="high",
        messages=[
            {"role": "system", "content": system_prompt_with_goal},
            {"role": "user", "content": user_prompt},
        ],
    )

    reply = response.choices[0].message.content.strip()

    # ----------------------------------------------------------------------------------
    # 2. Persist any memory the LLM wants to write
    # ----------------------------------------------------------------------------------
    try:
        maybe_json = json.loads(reply)
        memory_update = maybe_json.get("memory_to_write") if isinstance(maybe_json, dict) else None
    except Exception:
        memory_update = None

    if memory_update:
        append_note(memory_update)
        add_event("memory_write")
    try:
        actions = json.loads(reply)
    except json.JSONDecodeError:
        print("[WARN] LLM returned invalid JSON. Skipping iteration.")
        return

    action = actions.get("action")

    if action == "modify_files":
        _apply_full_writes(root, actions.get("changes", []))
    elif action == "create_files":
        _apply_full_writes(root, actions.get("changes", []))
    elif action == "append_files":
        # simple append implementation
        for change in actions.get("changes", []):
            rel_path = change["path"].lstrip("/\\")
            target = root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as fp:
                fp.write(change["content"])
            print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Appended to {rel_path}")
    elif action == "patch_files":
        _apply_patches(root, actions.get("changes", []))
    elif action == "human_help":
        print("[AGENT] Requests human assistance:\n" + actions.get("message_to_human", ""))
    elif action == "no_op":
        print("[AGENT] No changes proposed this iteration.")
    else:
        print(f"[WARN] Unknown action '{action}'. Skipping.")

    # Delete seed.txt on first run
    seed_file = root / "seed.txt"
    if seed_file.exists():
        seed_file.unlink()
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Deleted {seed_file}")

# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def main():
    project_root = Path(__file__).parent.resolve()
    agent_step(project_root, model="o3-ver1")


if __name__ == "__main__":
    main()
