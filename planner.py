
"""Task-planning component for SelfCoder.

The Planner converts the long-term GOAL (from goal.md) plus the current
codebase state into a list of short, actionable tasks.
"""
from pathlib import Path
import json, os, datetime, inspect
from llm_utils import chat_completion

_ROOT = Path(__file__).parent

def _load_goal() -> str:
    return (_ROOT / "goal.md").read_text(encoding="utf-8").strip()

def _snapshot_codebase(max_chars: int = 4000) -> str:
    parts = []
    for p in _ROOT.rglob("*.py"):
        if "venv" in p.parts or ".venv" in p.parts:
            continue
        try:
            parts.append(f"## {p}\n{p.read_text()}")
        except Exception:
            continue
    return "\n".join(parts)[:max_chars]

class Planner:
    def __init__(self, model: str = "o4-mini"):
        self.model = model

    def plan(self, n_tasks: int = 3):
        messages = [
            {
                "role": "system",
                "content": "You are a senior software architect helping an autonomous coding agent break down goals."
            },
            {
                "role": "user",
                "content": f"GOAL:\n{_load_goal()}\n\nCodebase snapshot:\n{_snapshot_codebase()}\n\nProduce {n_tasks} high-impact, bite-sized tasks the agent can attempt next."
            }
        ]
        reply = chat_completion(messages, preferred_model=self.model)
        # Try to parse bullets/JSON; fallback to raw text
        tasks = []
        try:
            tasks = json.loads(reply)
            if isinstance(tasks, list):
                return tasks
        except Exception:
            pass
        # Fallback: split by newline bullets
        for line in reply.splitlines():
            line = line.strip(" -*0123456789.\t")
            if line:
                tasks.append(line)
        return tasks

if __name__ == "__main__":
    print(Planner().plan())
