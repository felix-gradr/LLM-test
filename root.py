from __future__ import annotations

import json
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

from openai import AzureOpenAI

load_dotenv(override=True)

# File types that the agent is allowed to read/write.  Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md"}

# Memory file where short summaries of every iteration will be stored.
MEMORY_PATH = Path(__file__).parent / "memory.log"
MEMORY_CHAR_LIMIT = 4000  # ~ 1k tokens

# Load SYSTEM_PROMPT from prompt.txt
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8").strip()

# Load goal from goal.md
GOAL = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()


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
            # Match if the path starts with the directory pattern
            if rel_path.startswith(pattern):
                return True
            # Also match against the pattern with a wildcard for files inside
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


# ------------------------------  MEMORY  ------------------------------------

def _load_memory(max_chars: int = MEMORY_CHAR_LIMIT) -> str:
    """Return the last *max_chars* of memory or empty string."""
    if not MEMORY_PATH.is_file():
        return ""
    text = MEMORY_PATH.read_text(encoding="utf-8")
    return text[-max_chars:]


def _append_memory(snippet: str):
    """Append *snippet* to the memory file with a timestamp."""
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    MEMORY_PATH.write_text(f"[{timestamp}] {snippet}\n", encoding="utf-8", errors="ignore", append=True) if hasattr(Path, 'write_text') else open(MEMORY_PATH, 'a', encoding='utf-8').write(f"[{timestamp}] {snippet}\n")


# ------------------------------  AGENT LOOP  --------------------------------

def agent_step(root: Path, model: str = "o3-ver1") -> None:
    global GOAL
    """Run one reasoning / coding cycle."""

    # Gather current snapshot of the code base (truncated)
    snapshot = read_codebase(root)
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:12000]

    # Retrieve memory excerpt to provide continuity across iterations
    memory_excerpt = _load_memory()

    user_prompt = (
        f"Today is {datetime.utcnow().date()}.\n"
        f"Your GOAL: {GOAL}\n\n"
        f"Here is relevant MEMORY from previous iterations (last {len(memory_excerpt)} chars):\n{memory_excerpt}\n\n"
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

    # Persist raw reply to memory before attempting to parse (helps debugging)
    _append_memory(reply)

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

    # Delete seed.txt (only relevant for the first run)
    seed_file = root / "seed.txt"
    if seed_file.exists():
        seed_file.unlink()
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] Deleted {seed_file}")


def main():
    project_root = Path(__file__).parent.resolve()
    agent_step(project_root)


if __name__ == "__main__":
    main()
