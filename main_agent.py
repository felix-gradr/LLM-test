
"""
LLM-powered main agent for SelfCoder.

New architecture:
    1. modular_agent.run() – high-level Planner/Coder loop.
    2. fallback.agent_step() – low-level iterative self-coding (legacy).

The modular agent is lightweight for now, but allows structured growth.
"""
from pathlib import Path
import traceback

import modular_agent
import fallback

def run(model: str = "o3-ver1") -> None:
    project_root = Path(__file__).parent
    try:
        modular_agent.run(model=model)
    except Exception as exc:
        print(f"[WARN] modular_agent error: {exc}")
        traceback.print_exc()

    # Always invoke fallback to preserve previous behavior & ensure progress
    print("[MAIN_AGENT] Delegating to fallback.agent_step ...")
    fallback.agent_step(project_root, model=model)
