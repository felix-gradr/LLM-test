from __future__ import annotations

import json
import os
import traceback
from dotenv import load_dotenv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ------------- SAFETY: EARLY BACKUP -------------
_project_root = Path(__file__).resolve().parent
_backup_dir = _project_root / ".backup"
_backup_dir.mkdir(exist_ok=True)
_now_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
_backup_path = _backup_dir / f"root_{_now_ts}.py"
try:
    if not _backup_path.exists():  # avoid accidental overwrite
        _backup_path.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
except Exception:
    # Even backup must never crash execution
    pass
# ------------------------------------------------

from openai import AzureOpenAI

load_dotenv(override=True)

CODE_EXTENSIONS = {".py", ".txt", ".md"}
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text(encoding="utf-8").strip()
GOAL = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()


def _handle_root_error(e: Exception, project_root: Path) -> None:
    """Log the exception and ensure the agent can continue safely."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": str(e),
        "traceback": traceback.format_exc(),
    }
    try:
        with (project_root / "root_error.log").open("a", encoding="utf-8") as f:
            json.dump(log_entry, f)
            f.write("\n")
    except Exception:
        pass  # Logging itself must never crash
    print("[root.py] Fallback engaged due to unhandled error:", e, flush=True)


def _read_gitignore(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    patterns: list[str] = []
    for line in gitignore.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _is_ignored(path: Path, root: Path, ignore_patterns: list[str]) -> bool:
    import fnmatch
    rel_path = str(path.relative_to(root).as_posix())
    for pattern in ignore_patterns:
        if pattern.endswith("/"):  # directory pattern
            if rel_path.startswith(pattern) or fnmatch.fnmatch(rel_path, pattern + "*"):
                return True
        elif "/" not in pattern:  # filename glob
            if fnmatch.fnmatch(path.name, pattern):
                return True
        else:  # path glob
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
            except UnicodeDecodeError:
                continue
    return files


# --------- NEW: GUARDED LLM CALL ---------
def _call_llm(messages: list[dict[str, str]], model: str = "o3-ver1") -> str | None:
    """Call Azure LLM, returning response text. On failure, log and return None."""
    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_KEY"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version="2025-03-01-preview",
        )
        response = client.chat.completions.create(model=model, messages=messages)
        return response.choices[0].message.content.strip()
    except Exception as e:
        _handle_root_error(e, Path(__file__).parent.resolve())
        return None
# -----------------------------------------


def agent_step(root: Path, model: str = "o3-ver1") -> None:
    snapshot = read_codebase(root)
    joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:100_000]
    user_prompt = (
        f"Today is {datetime.now(timezone.utc).date()}.\n"
        f"Here is the current codebase (truncated):\n{joined}"
    )
    system_prompt_with_goal = f"{SYSTEM_PROMPT}\n\n ================================== Current GOAL:\n{GOAL}"

    messages = [
        {"role": "system", "content": system_prompt_with_goal},
        {"role": "user", "content": user_prompt},
    ]
    reply = _call_llm(messages, model=model)
    if reply is None:
        # LLM unavailable; skip this iteration but keep process alive
        print("[root.py] Skipping agent execution this iteration due to LLM failure.", flush=True)
        return

    print("[AGENT] Executing code:\n" + reply)
    try:
        exec(reply, globals())
    except Exception as e:
        _handle_root_error(e, root)


def main():
    project_root = Path(__file__).parent.resolve()
    try:
        agent_step(project_root, model="o3-ver1")
    except Exception as e:
        # Any uncaught exceptions inside agent_step should be logged
        _handle_root_error(e, project_root)


if __name__ == "__main__":
    main()
