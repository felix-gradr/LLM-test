
from __future__ import annotations
import os
from datetime import datetime, timezone
from pathlib import Path
from openai import AzureOpenAI
from error_logger import log_error
from helpers import read_codebase

def _call_llm(system: str, user: str, model: str = "o3-ver1") -> str:
    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_KEY"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version="2025-03-01-preview",
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        log_error("planner_agent._call_llm", exc)
        raise

def run(project_root: Path) -> None:
    """Create / update current_plan.md based on the latest codebase and goals"""
    goal = (project_root / "goal.md").read_text(encoding="utf-8").strip()
    snapshot = read_codebase(project_root)
    plan_path = project_root / "current_plan.md"
    current_plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""

    system_prompt = """You are the PLANNING agent for SelfCoder.
You specialise in analysing the current repository state, long-term goal, and sub-goal.
You output ONLY valid Python code that overwrites or creates a file called 'current_plan.md'.
The plan must be:
- A concise, ordered TODO list for the EXECUTION agent to follow this iteration.
- Written in clear markdown bullet points.
IMPORTANT: Do not modify any other files, print statements, or perform network calls.
Return ONLY the Python code. No markdown fences."""

    user_prompt = f"""Today is {datetime.now(timezone.utc).date()}.
Long-term & sub-goals:
{goal}

Existing plan (may be empty):
{current_plan}

Codebase snapshot (truncated):
{snapshot}
"""

    code_response = _call_llm(system_prompt, user_prompt)
    # Execute returned code in isolated namespace
    try:
        exec(code_response, {'Path': Path, '__name__': '__planner_exec__'})
    except Exception as exc:
        log_error("planner_agent.run: error executing planner code", exc)
        raise
