from __future__ import annotations

"""Root entry-point for SelfCoder.

This file orchestrates a *single* reasoning / coding iteration.  It is purposely
kept self-contained so that we can evolve it in-place without having to touch too
many other parts of the codebase.  The most important addition in this revision
is a *surgical editing* capability (``edit_files`` action) **plus** a compile
safety-net that automatically rolls back changes that would break the Python
codebase.
"""

import importlib
import json
import os
import py_compile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AzureOpenAI

from memory import Memory
from tools import registry as TOOL_REGISTRY  # Generic tool registry
from tools.web_search import duckduckgo_search  # Backward-compat alias

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Configuration & constants
# ---------------------------------------------------------------------------
CODE_EXTENSIONS = {".py", ".txt", ".md"}  # Expand later if needed
CONTEXT_WINDOW = 12_000  # ~12k characters of code + prompt per request
LOOP_NO_OP_LIMIT = 3  # How many consecutive no-ops are considered a loop

# System prompt and immutable goal (goal.md is immutable!)
PROJECT_ROOT = Path(__file__).parent.resolve()
SYSTEM_PROMPT = (PROJECT_ROOT / "system_prompt.txt").read_text(encoding="utf-8").strip()
GOAL = (PROJECT_ROOT / "goal.md").read_text(encoding="utf-8").strip()

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


# ---------------------------------------------------------------------------
#   Safe file mutations helpers  ────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _snapshot_files(root: Path, rel_paths: List[str]) -> Dict[str, str | None]:
    """Return a mapping *abs_path* → *old_content | None* for the given files."""
    snap: Dict[str, str | None] = {}
    for rel in rel_paths:
        abs_path = (root / rel).resolve()
        if abs_path.exists():
            try:
                snap[str(abs_path)] = abs_path.read_text(encoding="utf-8")
            except Exception:
                snap[str(abs_path)] = None  # Binary or unreadable – treat as None
        else:
            snap[str(abs_path)] = None  # File did not exist yet
    return snap


def _restore_snapshot(snap: Dict[str, str | None]):
    """Restore files from *_snapshot_files* output – delete new files, revert mods."""
    for abs_path_str, content in snap.items():
        path = Path(abs_path_str)
        if content is None:
            # Newly created file → remove if still exists
            if path.exists():
                try:
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        shutil.rmtree(path)
                except Exception:
                    pass
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def _compile_project(root: Path) -> bool:
    """Return *True* if the entire project compiles, *False* otherwise."""
    try:
        for py_path in root.rglob("*.py"):
            py_compile.compile(str(py_path), doraise=True)
        return True
    except py_compile.PyCompileError as exc:
        print(f"[COMPILE-ERROR] {exc.msg} in {exc.file}")
        return False


# ---------------------------------------------------------------------------
#   File mutation primitives exposed to the LLM  ────────────────────────────
# ---------------------------------------------------------------------------

def create_or_replace_files(root: Path, changes: List[Dict[str, Any]]) -> bool:
    """Create **or** fully replace files.  Rollback if compilation fails."""
    rel_paths = [c["path"].lstrip("/\\") for c in changes]
    snap = _snapshot_files(root, rel_paths)

    # Apply changes
    for change in changes:
        rel_path = change["path"].lstrip("/\\")
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change["content"], encoding="utf-8")
        print(f"[WRITE] {rel_path}")

    if _compile_project(root):
        return True

    # Failed – rollback
    print("[ROLLBACK] Reverting create/replace changes – compile failed.")
    _restore_snapshot(snap)
    return False


def append_to_files(root: Path, changes: List[Dict[str, Any]]) -> bool:
    rel_paths = [c["path"].lstrip("/\\") for c in changes]
    snap = _snapshot_files(root, rel_paths)

    for change in changes:
        rel_path = change["path"].lstrip("/\\")
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if target.exists() else "w"
        with target.open(mode, encoding="utf-8") as fh:
            fh.write(change["content"])
        print(f"[APPEND] {rel_path}")

    if _compile_project(root):
        return True

    print("[ROLLBACK] Reverting append changes – compile failed.")
    _restore_snapshot(snap)
    return False


def edit_files(root: Path, edits: List[Dict[str, Any]]) -> bool:
    """Surgically edit existing files using a *search & replace* spec.

    Each *edits* item must have:
        {"path": "file.py", "search": "old", "replace": "new", "count": 1}
    *count* is optional (defaults to 1 – first occurrence only, keeps diffs minimal).
    """
    rel_paths = [e["path"].lstrip("/\\") for e in edits]
    snap = _snapshot_files(root, rel_paths)

    for spec in edits:
        rel_path = spec["path"].lstrip("/\\")
        target = root / rel_path
        if not target.exists():
            print(f"[EDIT-WARN] {rel_path} does not exist – skipping.")
            continue
        text = target.read_text(encoding="utf-8")
        new_text, n = text.replace(spec["search"], spec["replace"], spec.get("count", 1)), None
        if text == new_text:
            print(f"[EDIT-INFO] No occurrence found in {rel_path} – skipping.")
            continue
        target.write_text(new_text, encoding="utf-8")
        print(f"[EDIT] {rel_path} – applied search & replace.")

    if _compile_project(root):
        return True

    print("[ROLLBACK] Reverting edits – compile failed.")
    _restore_snapshot(snap)
    return False


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
    memory_snippet = json.dumps(memory.data, indent=2)[:2000]

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
    success = True  # did the requested action succeed?

    # --------------------------
    # File manipulation actions
    # --------------------------
    if action in {"modify_files", "create_files"}:
        success = create_or_replace_files(project_root, actions.get("changes", []))

    elif action == "append_files":
        success = append_to_files(project_root, actions.get("changes", []))

    elif action == "edit_files":
        success = edit_files(project_root, actions.get("changes", []))

    # -------------
    # Tool calling
    # -------------
    elif action == "call_tool":
        tool_name = actions.get("tool")
        if tool_name not in TOOL_REGISTRY:
            print(f"[WARN] Requested unknown tool '{tool_name}'.")
            success = False
        else:
            kwargs = actions.get("args", {}) or {}
            try:
                result = TOOL_REGISTRY[tool_name](**kwargs)
                print("[TOOL] {} result:\n{}".format(tool_name, json.dumps(result, indent=2)[:1000]))
                # Persist last tool call so it can be referenced later
                memory.data.setdefault("tool_history", []).append({
                    "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
                    "tool": tool_name,
                    "args": kwargs,
                    "result": result,
                })
                # Trim history to last 10 calls
                memory.data["tool_history"] = memory.data["tool_history"][-10:]
            except Exception as exc:
                print(f"[ERROR] Tool '{tool_name}' failed: {exc}")
                success = False

    # --------------
    # Legacy web_search alias
    # --------------
    elif action == "web_search":
        query = actions.get("query", "").strip()
        if query:
            result = duckduckgo_search(query)
            print("[WEB-SEARCH] Results for '{}':\n{}".format(query, json.dumps(result, indent=2)[:1000]))
            memory.data["last_search"] = {
                "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
                "query": query,
                "result": result,
            }
        else:
            print("[WARN] web_search action received without a query string.")
            success = False

    # ---------------
    # Human help
    # ---------------
    elif action == "human_help":
        print("[AGENT] Requests human assistance:\n" + actions.get("message_to_human", ""))

    # -----------
    # No-op / unknown
    # -----------
    else:
        print(f"[INFO] No recognised action – received '{action}'. Treating as no_op.")
        action = "no_op"
        success = False

    # --------------------------------------------------
    # 5. Memory bookkeeping
    # --------------------------------------------------
    if action == "no_op" or not success:
        memory.data["consecutive_no_op"] = memory.data.get("consecutive_no_op", 0) + 1
    else:
        memory.data["consecutive_no_op"] = 0

    memory.increment_iteration()
    memory.record_reply(reply, action)
    memory.save()

    print(f"[AGENT] Iteration {memory.data['iteration']} complete – action: {action} – success: {success}")


if __name__ == "__main__":  # Support `python -m root`
    agent_step(PROJECT_ROOT)
