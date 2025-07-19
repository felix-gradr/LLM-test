
##FALL BACK AGENT; EDIT WITH EXTREME CAUTION
from __future__ import annotations

import os
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

from error_logger import log_error

load_dotenv(override=True)

# File types that the agent is allowed to read/write. Adjust as needed.
CODE_EXTENSIONS = {".py", ".txt", ".md"}

# Load prompts & goal
ROOT = Path(__file__).parent
SYSTEM_PROMPT = (ROOT / "system_prompt.txt").read_text(encoding="utf-8").strip()
GOAL = (ROOT / "goal.md").read_text(encoding="utf-8").strip()

# --------------- Helper functions --------------- #
def _read_gitignore(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    patterns: list[str] = []
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _is_ignored(path: Path, root: Path, ignore_patterns: list[str]) -> bool:
    import fnmatch

    rel_path = path.relative_to(root).as_posix()
    for pattern in ignore_patterns:
        if pattern.endswith("/"):  # dir pattern
            if rel_path.startswith(pattern) or fnmatch.fnmatch(rel_path, pattern + "*"):
                return True
        elif "/" not in pattern:  # filename pattern, e.g. *.log
            if fnmatch.fnmatch(path.name, pattern):
                return True
        else:  # glob with slash
            if fnmatch.fnmatch(rel_path, pattern):
                return True
    return False


def read_codebase(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    ignore_patterns = _read_gitignore(root)
    for path in root.rglob("*"):
        if path.is_dir() or _is_ignored(path, root, ignore_patterns):
            continue
        if path.suffix in CODE_EXTENSIONS and path.is_file():
            try:
                files[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
            except Exception as e:  # pragma: no cover
                # Could be binary or bad encoding – skip but log for visibility
                log_error(f"read_codebase: unable to read {path}", e)
    return files


# --------------- Core fallback agent --------------- #
def agent_step(root: Path, model: str = "o3-ver1") -> None:
    """Perform a single fallback reasoning / coding cycle.

    All errors are logged using error_logger.log_error so that the main
    iteration never silently fails.
    """
    # Snapshot current codebase
    snapshot: dict[str, str] = read_codebase(root)

    # Truncate snapshot to reasonable length (100k chars)
    joined_snapshot = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:100_000]

    user_prompt = (
        f"Today is {datetime.now(timezone.utc).date()}.\n"
        f"Here is the current codebase (truncated):\n{joined_snapshot}"
    )

    system_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f" ================================== Current GOAL:\n{GOAL}"
    )

    # Prepare OpenAI client
    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_KEY"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version="2025-03-01-preview",
        )
    except Exception as e:
        # Critical – we cannot even build the client
        log_error("fallback.agent_step: failed to initialise AzureOpenAI", e)
        return  # Early exit – nothing we can do now

    # Query the model
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        log_error("fallback.agent_step: OpenAI completion error", e)
        return

    # Execute the returned code
    print("[FALLBACK] Executing model-generated code:")
    print(reply)
    try:
        exec(reply, globals(), locals())
    except Exception as e:
        log_error("fallback.agent_step: error executing LLM code", e)
        print(f"[FALLBACK WARN] Execution error: {e}")
