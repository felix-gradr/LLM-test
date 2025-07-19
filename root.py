from __future__ import annotations

import json
import os
import memory
import traceback
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


def agent_step(root: Path) -> None:
    """
    Run one full reasoning/coding cycle using the orchestrator.

    Pipeline:
        1. Run baseline tests – abort early if red.
        2. Snapshot current codebase for safety rollback.
        3. Ask TaskRouter (Light+Heavy LLM chain) for a code-patch.
        4. Exec the patch under a safety snapshot.
        5. Validate compilation & post-patch tests; rollback on failure.
    """
    # 1. Baseline tests
    if not run_tests(verbosity=1):
        print("[TESTS] Baseline tests failing – aborting iteration.")
        return

    # 2. Snapshot codebase as {rel_path: source}
    snapshot = read_codebase(root)

    # 3. Get code-patch from hierarchical LLM agents
    try:
        router = TaskRouter(snapshot, GOAL, SYSTEM_PROMPT)
        patch_code = router.generate()
    except Exception as exc:
        print(f"[LLM] Failed to obtain patch: {exc}")
        memory.log_error(exc, context="TaskRouter.generate()")
        return

    # 4. Safety wrapper around exec
    _pre_snapshot = _snapshot_py_files(root)
    try:
        exec(patch_code, globals())
    except Exception as exc:
        print(f"[EXEC] Error while applying patch: {exc}")
        memory.log_error(exc, context="exec(patch_code)")
        _restore_snapshot(root, _pre_snapshot)
        return

    # 5. Validate compilation & tests post-patch
    if not _validate_codebase(root):
        print("[SAFETY] Compilation failed after patch – rolling back.")
        _restore_snapshot(root, _pre_snapshot)
        return

    if not run_tests(verbosity=1):
        print("[TESTS] Post-patch tests failing – rolling back.")
        _restore_snapshot(root, _pre_snapshot)
        return

    print("[OK] Patch applied successfully and all tests green.")

def main():
    project_root = Path(__file__).parent.resolve()
    agent_step(project_root, model="o3-ver1")


if __name__ == "__main__":
    main()
from orchestrator import TaskRouter
