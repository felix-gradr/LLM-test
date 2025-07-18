# SelfCoder – Long-Term Plan

This document is **mutable** and acts as the high-level roadmap that spans
multiple iterations.  It should be updated *incrementally* – big-bang edits
are discouraged because they hide context in the diff.

## Phase 1 – Core Infrastructure (current)

Goal: fulfil the *Current Sub-goal* outlined in `goal.md` – memory, safety,
loop-protection.

- [X] Introduce structured memory (`memory_manager.py`).
- [ ] Wire the new memory manager into `root.py` (safe, staged rollout).
- [ ] Devise & implement loop-protection heuristics (detect identical diffs).
- [ ] Add lightweight tests to protect critical files from accidental damage.

## Phase 2 – Self-Improvement Framework

Goal: iterate on plans, tests, and analysis to continuously enhance the agent.

- [ ] Implement multi-LLM orchestration (analyst, coder, reviewer roles).
- [ ] Add scoring metrics to evaluate each iteration (e.g., test pass rate,
  cyclomatic complexity, etc.).
- [ ] Create a feedback loop – unsuccessful iterations trigger reflections &
  corrective actions stored via `memory_manager`.

## Phase 3 – External Integration (future, not started)

Goal: once the agent is robust, begin exploring the *future goal* (SAAS).

- [ ] Research market opportunities.
- [ ] Prototype minimum-viable product.
- [ ] …
