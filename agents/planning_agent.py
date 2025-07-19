
"""Strategic high-level planner (o3).

The PlanningAgent’s responsibility is **thinking, not coding**.  Given the
immutable goal, current sub-goal, and an up-to-date repository summary, it
emits a *machine-readable* JSON plan that can be consumed by downstream
agents.

The agent intentionally avoids touching concrete implementation details so
that its output remains stable when the codebase changes.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

from llm_helper import ask_o3


SYSTEM_PROMPT = """    You are the PLANNING agent inside a multi-agent autonomous coding system.
Your sole job is to craft *strategy*, NOT code.

1. Read the project’s immutable GOAL and current sub-goal (provided below).
2. Read a short repository summary (also provided below).
3. Output ONLY valid JSON with the following keys:
   - short_term_plan:  list[str]     # 1–3 items achievable in ≤2 iterations
   - long_term_plan:   list[str]     # vision for subsequent milestones
   - rationale:        str           # Why these plans are chosen
No additional keys, no markdown, no commentary – just the JSON payload.
"""


def generate(repo_summary: str, goal_text: str) -> Dict[str, Any]:
    """Return the strategic plan as a Python dict."""
    user_prompt = f"""        GOAL + Sub-goal:
    {goal_text}

    Repository summary:
    {repo_summary}

    ===
    Produce the planning JSON now.
    """

    response = ask_o3(user_prompt, system_prompt=SYSTEM_PROMPT)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Graceful degradation – still return something parseable
        return {
            "short_term_plan": [],
            "long_term_plan": [],
            "rationale": "PlanningAgent: failed to parse JSON – raw response stored.",
            "_raw": response,
        }
