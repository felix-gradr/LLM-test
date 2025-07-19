from __future__ import annotations

import json
import os
from test_runner import run_tests
from dotenv import load_dotenv
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------- #
#  Code-safety helpers (auto-inserted by SelfCoder)
# ---------------------------------------------------------------------- #
from typing import Dict

def _snapshot_py_files(root: Path) -> Dict[str, str]:
    """Return a mapping of relative .py paths to their source code."""
    snap: Dict[str, str] = {}
    for p in root.rglob("*.py"):
        try:
            snap[str(p.relative_to(root))] = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return snap

def _restore_snapshot(root: Path, snap: Dict[str, str]) -> None:
    """Restore files from a snapshot, deleting any new files."""
    existing_paths = {str(p.relative_to(root)) for p in root.rglob("*.py")}
    snap_paths = set(snap)
    # Restore or overwrite files that existed in the snapshot
    for rel, src in snap.items():
        (root / rel).write_text(src, encoding="utf-8")
    # Remove new files created after the snapshot
    for rel in existing_paths - snap_paths:
        (root / rel).unlink(missing_ok=True)

def _validate_codebase(root: Path) -> bool:
    """Attempt to compile every .py file. Return True if all compile."""
    import builtins
    for p in root.rglob("*.py"):
        try:
            source = p.read_text(encoding="utf-8")
            compile(source, str(p), "exec")
        except Exception as e:
            print(f"[SAFETY] Compilation failed for {p}: {e}")
            return False
    return True


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
                # Skip binary or non‑UTF8 files
                continue
    return files


def agent_step(root: Path, model: str = "o3") -> None:
    """Run one reasoning / coding cycle."""
    # Run baseline tests before making any changes
    if not run_tests(verbosity=1):
        print("[TESTS] Baseline tests failing. Aborting agent step.")
        return
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
    
    try:

# === SAFETY EXECUTION WRAPPER ===
            _pre_snapshot = _snapshot_py_files(root)
            try:
                exec(reply, globals())
            except Exception as e:
                print(f"[WARN] Error executing code: {e}")
                _restore_snapshot(root, _pre_snapshot)
            else:
                if not _validate_codebase(root):
                    print("[WARN] Validation failed, rolling back changes.")
                    _restore_snapshot(root, _pre_snapshot)

    except Exception as e:
        print(f"[WARN] Error executing code: {e}")


def main():
    project_root = Path(__file__).parent.resolve()
    agent_step(project_root, model="o3-ver1")


if __name__ == "__main__":
    main()
