"""LLM-powered main agent for SelfCoder.

This agent intentionally avoids any hard-coded logic beyond:
1. Taking a snapshot of the current repository (respecting .gitignore).
2. Asking an LLM (Azure OpenAI) what to do next.
3. Executing the returned Python code.
"""

from __future__ import annotations

import os
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

# Re-use utilities from fallback to avoid duplication
from fallback import read_codebase, SYSTEM_PROMPT

# Load the immutable, human-written GOAL
GOAL_TEXT = (Path(__file__).parent / "goal.md").read_text(encoding="utf-8").strip()


def _has_creds() -> bool:
    load_dotenv(override=True)
    return bool(os.getenv("AZURE_KEY") and os.getenv("AZURE_ENDPOINT"))


def run(model: str = "o4-mini") -> None:
    """Run one intelligent, LLM-driven self-improvement iteration."""
    if not _has_creds():
        print("[MAIN_AGENT] Azure credentials missing; skipping LLM step.")
        return  # Root will fall back or at least log progress.

    root = Path(__file__).parent
    snapshot = read_codebase(root)
    joined = (
        "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())[:100_000]
    )  # keep context manageable

    user_prompt = (
        f"Today is {datetime.now(timezone.utc).date()}.\n"
        f"Here is the current codebase (truncated):\n{joined}"
    )

    system_prompt = f"{SYSTEM_PROMPT}\n\n ================================== Current GOAL:\n{GOAL_TEXT}"

    client = AzureOpenAI(  # type: ignore[call-arg]
        api_key=os.getenv("AZURE_KEY"),
        azure_endpoint=os.getenv("AZURE_ENDPOINT"),
        api_version="2025-03-01-preview",
    )

    print("[MAIN_AGENT] Querying LLM …")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    reply = response.choices[0].message.content.strip()
    print("[MAIN_AGENT] Executing returned code:\n" + reply)
    try:
        exec(reply, globals())
    except Exception as exc:
        print("[MAIN_AGENT] Error while executing LLM code:", exc)
        traceback.print_exc()
