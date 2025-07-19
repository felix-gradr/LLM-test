
# Long-Term Plan for SelfCoder

This document outlines a staged roadmap to turn SelfCoder into a robust,
continuously self-improving autonomous coding system while **never**
getting completely stuck.

## Stage 0 – Bootstrapping (✓)
• Ensure every `python -m root` invocation makes visible progress by logging a
  timestamp.
• Provide a minimal `main_agent.run()` stub so that the fallback agent is used
  only if something genuinely breaks.
• Guard the fallback agent behind environment checks to avoid crashes when no
  Azure credentials are configured.

## Stage 1 – Iterative Self-Improvement
1. Implement a lightweight “code-review” loop:
   – Snapshot the codebase.
   – Call the LLM (o3-ver1 locally, o4-mini for more demanding tasks) to
     suggest incremental improvements.
   – Apply patches automatically.
   – Validate by running test commands (e.g. `python -m root`).
2. Introduce automatic rollback if a new iteration causes exceptions.

## Stage 2 – Capability Expansion
• Add static analysis (e.g. `ruff`, `mypy`), enforce formatting (`black`).
• Integrate tests and coverage metrics; require test pass before committing a
  change.
• Build a plugin system to let specialized sub-agents (doc writer, test
  writer, refactorer) coordinate via shared state.

## Stage 3 – Distributed & Parallel Reasoning
• Orchestrate multiple LLM calls in parallel, aggregate results, and choose
  the best patch via majority vote or heuristic scoring.
• Cache prompts/responses for reproducibility.

## Stage 4 – Human-in-the-Loop Excellence
• Provide clear, minimal requests for costly human interventions (package
  installs, API keys, etc.), batching whenever possible.
• Maintain a changelog and “explainability” report so a human can audit
  decisions quickly.

## Stage 5 – Autonomous Project Generator
• Leverage the improved framework to spin up entirely new repositories,
  scaffold projects, and maintain multiple codebases.

---
*Last updated automatically on* **2025-07-19**