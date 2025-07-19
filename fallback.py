##FALL BACK AGENT; EDIT WITH EXTREME CAUTION

from __future__ import annotations

import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from pathlib import Path

from openai import AzureOpenAI

load_dotenv(override=True)

# File types that the agent is allowed to read/write.  Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md"}

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
            # Skip binary-ish files
            continue
                # Skip binary or non‑UTF8 files
                continue
    return files

def agent_step(root: Path, model: str = "o3") -> None:
    """Run one reasoning / coding cycle."""
    snapshot = read_codebase(root)
    # Truncate to avoid blowing past context limits
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:100000]

    user_prompt = (
        f"Today is {datetime.now(timezone.utc).date()}.\n"
        f"Here is the current codebase (truncated):\n{joined}"
    )

    # Add GOAL to the system prompt
    SYSTEM_PROMPT_WITH_GOAL = f"{SYSTEM_PROMPT}\n\n ================================== Current GOAL:\n{GOAL}"

    client = AzureOpenAI(
            api_key=os.getenv("AZURE_KEY"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version="2025-03-01-preview",
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_WITH_GOAL},
            {"role": "user", "content": user_prompt},
        ],
    )

    reply = response.choices[0].message.content.strip()
    
    print("[AGENT] Executing code:\n" + reply)
    try:
        exec(reply, globals())
    except Exception as e:
        print(f"[WARN] Error executing code: {e}")



# == Patched for local LLM support ==
from llm_utils import chat_completion as _sc_chat_completion

# Shadow previous definition with a more resilient one
def agent_step(root, model: str = "o3-ver1") -> None:  # type: ignore[override]
    """Enhanced agent_step supporting Azure, public OpenAI, or stub."""
    snapshot = read_codebase(root)
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:100000]

    user_prompt = (
        f"Today is {datetime.now(timezone.utc).date()}.\n"
        f"Here is the current codebase (truncated):\n{joined}"
    )

    system_with_goal = f"{SYSTEM_PROMPT}\n\n ================================== Current GOAL:\n{GOAL}"
    messages = [
        { "role": "system", "content": system_with_goal },
        { "role": "user", "content": user_prompt },
    ]

    reply = _sc_chat_completion(messages, preferred_model=model)
    print("[AGENT] Executing code:\n" + reply)
    try:
        exec(reply, globals())
    except Exception as e:
        print(f"[WARN] Error executing generated code: {e}")

if __name__ == "__main__":
    root = Path(__file__).parent
    print(f"Indexed {len(read_codebase(root))} files from {root}")