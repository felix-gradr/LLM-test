"""Task-planning component for SelfCoder.

This version focuses on a *curated* codebase snapshot so LLM context windows
remain clean and relevant.

Changes:
  • Skip virtual-envs, caches, logs and other auto-generated artefacts.
  • Respect a hard `max_chars` limit while iterating to avoid overshooting.
  • Request JSON list output from the LLM for easier parsing.
"""

from pathlib import Path
import json, datetime
from llm_utils import chat_completion

_ROOT = Path(__file__).parent

def _load_goal() -> str:
    return (_ROOT / "goal.md").read_text(encoding="utf-8").strip()

# Directories / files we never want in the LLM context
_IGNORE_DIRS = {"venv", ".venv", "__pycache__"}
_IGNORE_FILES = {
    "auto_progress.md",
    "latest_plan.json",
    "tester.log",
}

def _snapshot_codebase(max_chars: int = 4000) -> str:
    """Return a concise snapshot of relevant *.py files.

    1. Skip ignored directories/files.
    2. Accumulate until `max_chars` reached.
    3. Use UTF-8 with errors="ignore" to gracefully handle odd encodings.
    """
    parts, length = [], 0
    for p in sorted(_ROOT.rglob("*.py")):
        if any(tok in p.parts for tok in _IGNORE_DIRS):
            continue
        if p.name in _IGNORE_FILES:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue  # Binary or unreadable

        snippet = f"## {p.relative_to(_ROOT)}\n{txt}"
        snippet_len = len(snippet)
        if length + snippet_len > max_chars:
            snippet = snippet[: max_chars - length]
            parts.append(snippet)
            break

        parts.append(snippet)
        length += snippet_len
        if length >= max_chars:
            break

    return "\n".join(parts)

class Planner:
    def __init__(self, model: str = "o4-mini"):
        self.model = model

    def plan(self, n_tasks: int = 3):
        messages = [
            {
                "role": "system",
                "content": "You are a senior software architect helping an autonomous coding agent break down goals.",
            },
            {
                "role": "user",
                "content": (
                    f"UTC {datetime.datetime.utcnow().isoformat()}\n"
                    f"GOAL:\n{_load_goal()}\n\n"
                    f"Codebase snapshot (truncated):\n{_snapshot_codebase()}\n\n"
                    f"Please propose {n_tasks} high-impact, bite-sized tasks the agent can attempt next.\n"
                    f"Return ONLY a JSON list of task strings."
                ),
            },
        ]
        reply = chat_completion(messages, preferred_model=self.model)

        # Attempt to parse strict JSON list
        try:
            tasks = json.loads(reply)
            if isinstance(tasks, list) and all(isinstance(t, str) for t in tasks):
                return tasks
        except Exception:
            pass  # Fallback to bullet parsing below

        tasks = []
        for line in reply.splitlines():
            line = line.strip(" -*0123456789.\t")
            if line:
                tasks.append(line)
        return tasks

if __name__ == "__main__":
    print(Planner().plan())
