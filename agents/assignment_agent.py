
"""Task dispatcher that converts high-level plans into discrete worker tasks (o3)."""
from __future__ import annotations
import json
from typing import List, Dict

from llm_helper import ask_o3

SYSTEM_PROMPT = """    You are the ASSIGNMENT agent.

Input: A strategic plan (JSON) created by the Planning agent.
Output: STRICT JSON ‑- a list called `assignments`.  Each assignment is an
object with:
  task: short (<60 chars) worker instruction

Example output:
[
  { "task": "Refactor orchestrator to use new agent system" },
  { "task": "Write unit tests for planning_agent" }
]
No markdown, no additional keys.
"""


def generate(plan: dict) -> List[Dict[str, str]]:
    """Convert a plan dict into a list of worker-level tasks."""
    user_prompt = f"""Here is the current strategic plan:

    {json.dumps(plan, indent=2)}

    Craft the `assignments` JSON list now.
    """
    response = ask_o3(user_prompt, system_prompt=SYSTEM_PROMPT)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Fall back to a single generic task so the pipeline can continue
        return [{"task": "Fallback: implement missing AssignmentAgent JSON parsing"}]
