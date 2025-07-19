"""
LLM-powered main agent for SelfCoder.

This agent delegates to fallback.agent_step, ensuring LLM-based improvements.
"""

from pathlib import Path
import fallback

def run(model: str = "o3-ver1") -> None:
    """Run one intelligent, LLM-driven self-improvement iteration by delegating to fallback."""
    project_root = Path(__file__).parent
    print(f"[MAIN_AGENT] Delegating to fallback.agent_step with model: {model}")
    fallback.agent_step(project_root, model=model)
