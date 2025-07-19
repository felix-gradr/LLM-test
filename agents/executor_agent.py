
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
        log_error("executor_agent._call_llm", exc)
        raise

def run(project_root: Path) -> None:
    """Read the plan & perform code modifications accordingly"""
    goal = (project_root / "goal.md").read_text(encoding="utf-8").strip()
    plan_path = project_root / "current_plan.md"
    plan_content = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    snapshot = read_codebase(project_root)

    system_prompt = """You are the EXECUTION agent for SelfCoder.
Take the plan provided in 'current_plan.md' and implement it.
You may create/edit/remove files EXCEPT for 'goal.md' and '.env'.
When finished, ensure your python code prints nothing.
Return ONLY valid Python code to perform the changes.
Use pathlib for file operations and keep modifications minimal & atomic."""

    user_prompt = f"""Today is {datetime.now(timezone.utc).date()}.
Long-term & sub-goals:
{goal}

PLAN TO EXECUTE:
{plan_content}

Codebase snapshot (truncated):
{snapshot}
"""

    code_response = _call_llm(system_prompt, user_prompt)
    try:
        exec(code_response, {'Path': Path, '__name__': '__executor_exec__'})
    except Exception as exc:
        log_error("executor_agent.run: error executing executor code", exc)
        raise
