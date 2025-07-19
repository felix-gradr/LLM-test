# Long-Term Self-Improvement Plan

## Phase 0 – Foundations (current)
1. Ensure `python -m root` always completes without crashing.
2. Log every execution to `progress.log` for traceability.
3. Maintain a robust fallback agent.

## Phase 1 – Incremental Autonomy
1. Replace placeholder logic in `root.py` with a modular “main agent”.
2. Introduce a simple reflex-based improvement loop:
   • Read codebase snapshot  
   • Decide next action (edit / create files / call LLM)  
   • Apply change  
3. Keep edits small and reversible; always commit a safety checkpoint.

## Phase 2 – Multi-agent Orchestration
1. Spawn specialised sub-agents (planner, coder, tester, critic).
2. Share context via a lightweight in-repo knowledge base (`kb/` directory).
3. Use the strongest available model (`o4-mini`) for high-level planning.

## Phase 3 – Continuous Learning
1. Collect metrics (pass/fail, execution time, diff size) in `metrics.json`.
2. Use reinforcement signals to rank self-generated strategies.
3. Periodically refactor the codebase for clarity & performance.

## Phase 4 – Human Collaboration
1. Detect stagnant progress and request targeted human input.
2. Minimise human workload by providing clear, concise tasks.

---

Last updated: 2025-07-19 13:06:19 UTC
