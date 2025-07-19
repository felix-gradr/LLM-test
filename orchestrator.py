
"""orchestrator.py
High-level module that demonstrates *chained* LLM calls:
    • LightAgent  – cheap `o4-mini` summarisation & pattern-matching.
    • HeavyAgent  – expensive `o3-ver1` deep reasoning / code generation.

The public entry-point is TaskRouter.generate(), which first compresses
large context via LightAgent and then feeds that summary (plus goal) into
HeavyAgent to obtain a Python code-patch (to be executed by root.py).
"""

from __future__ import annotations
from typing import Dict

from llm_helper import ask_o4, ask_o3
import memory


class LightAgent:
    """Wrapper around the lightweight `o4-mini` model."""

    MODEL_NAME = "o4-mini"

    @staticmethod
    def summarise_codebase(snapshot: Dict[str, str]) -> str:
        """Return a condensed summary of *snapshot* suitable for o3 input."""
        joined = "\n".join(f"## {p}\n{c}" for p, c in snapshot.items())
        # Hard cap to stay under context window
        joined = joined[:40_000]
        prompt = (
            "You are tasked with producing a concise yet comprehensive summary " 
            "of a Python codebase so that a more powerful LLM can make informed " 
            "decisions without reading every file.\n\n" 
            "Please summarise the following codebase in <350 words, preserving:\n" 
            "• Key modules & their responsibilities\n" 
            "• Any obvious TODOs / FIXME comments\n" 
            "• Existing tests or CI hooks\n\n" 
            "Codebase follows:\n" 
            f"{joined}"
        )
        summary = ask_o4(prompt)
        memory.add_memory("Generated codebase summary", meta={"kind": "summary"})
        return summary


class HeavyAgent:
    """Wrapper around the heavyweight `o3-ver1` model."""

    MODEL_NAME = "o3-ver1"

    @staticmethod
    def propose_patch(summary: str, goal: str) -> str:
        """Ask the heavy model to propose a Python code-patch.

        The result *must* be a raw Python code block – root.py will `exec` it.
        """
        prompt = (
            f"You are SelfCoder, an autonomous coding agent.\n\n"
            f"Current immutable GOAL:\n{goal}\n\n"
            "You have been provided a high-level summary of the existing " 
            "repository. Using only that summary, decide on the single *most " 
            "useful* incremental change that advances the GOAL – e.g. create " 
            "new modules, refactor, write tests, etc.\n\n" 
            "Respond with **only** a valid Python code block that performs the " 
            "change (using pathlib for cross-platform compatibility).\n\n" 
            "Repository summary:\n" 
            f"{summary}"
        )
        code_block = ask_o3(prompt, temperature=0.0)
        memory.add_memory("Proposed code patch from HeavyAgent", meta={"kind": "patch"})
        return code_block


class TaskRouter:
    """Simple façade combining Light & Heavy agents."""

    def __init__(self, snapshot: Dict[str, str], goal: str, _system_prompt: str) -> None:
        self.snapshot = snapshot
        self.goal = goal
        self.system_prompt = _system_prompt  # Not used yet but kept for future

    # Public -----------------------------------------------------------------
    def generate(self) -> str:
        """Run the chained call pipeline and return a Python patch string."""
        summary = LightAgent.summarise_codebase(self.snapshot)
        patch_code = HeavyAgent.propose_patch(summary, self.goal)
        return patch_code

    # ==== MULTI AGENT v1 BEGIN ====
        def generate(self) -> str:  # noqa: C901, WPS231 – long method is acceptable here
            """Multi-step patch generation using planning, assignment and worker agents."""
            try:
                from pathlib import Path  # local import keeps global namespace clean
                import json
                import llm_helper  # already part of the repo

                # -------------------------------------------------
                # 1. Cheap repo summary (LightAgent, o4-mini)
                # -------------------------------------------------
                summary = self.light_agent.summarise_repository()

                # -------------------------------------------------
                # 2. High-level strategic plan (PlanningAgent, o3)
                # -------------------------------------------------
                goal_text = Path(__file__).with_name("goal.md").read_text(encoding="utf-8")
                planning_prompt = (
                    "You are the PLANNING agent for a self-developing codebase.\n"
                    "Produce a concise JSON dictionary with one key, 'plan', containing an ordered "
                    "list of high-level actions that move the project towards its immutable goal "
                    "and current sub-goal.\n\n"
                    f"Immutable goal & sub-goal:\n{goal_text}\n"
                    "Repository summary:\n"
                    f"{summary}\n"
                    "Respond with valid JSON ONLY."
                )
                plan_json_raw = llm_helper.ask_o3(planning_prompt)
                plan = json.loads(plan_json_raw).get("plan", [])
                if not plan:
                    raise ValueError("Planning agent returned an empty plan.")

                # -------------------------------------------------
                # 3. Concrete tasks (AssignmentAgent, o3)
                # -------------------------------------------------
                assignment_prompt = (
                    "You are the ASSIGNMENT agent.\n"
                    "Break the following strategic plan into the smallest possible, independent "
                    "coding tasks that can each be executed in a single patch.\n"
                    "Return a JSON list of task strings.\n\n"
                    f"Strategic plan JSON:\n{plan_json_raw}"
                )
                tasks_raw = llm_helper.ask_o3(assignment_prompt)
                tasks = json.loads(tasks_raw)
                if not tasks:
                    raise ValueError("Assignment agent produced no tasks.")
                current_task = tasks[0]

                # -------------------------------------------------
                # 4. Patch for first task (WorkerAgent, o4)
                # -------------------------------------------------
                worker_prompt = (
                    "You are the WORKER agent. Implement the requested change as a Python patch.\n"
                    "The patch MUST:\n"
                    " • Use pathlib for cross-platform file access\n"
                    " • Be enclosed in a single Python code block ( ... )\n"
                    " • Contain NO additional commentary.\n\n"
                    f"Immutable goal & sub-goal:\n{goal_text}\n"
                    f"Repository summary:\n{summary}\n"
                    f"Your task: {current_task}"
                )
                patch = llm_helper.ask_o4(worker_prompt)
                return patch

            except Exception as exc:  # pragma: no cover – safety net
                # If anything fails, fall back to the original single-step behaviour.
                try:
                    return self.heavy_agent.propose_patch()
                except Exception:
                    # Last-ditch effort: surface the error so it gets logged upstream.
                    raise exc
    # ==== MULTI AGENT v1 END ====
    