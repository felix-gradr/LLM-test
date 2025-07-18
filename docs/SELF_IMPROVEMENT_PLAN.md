# SelfCoder – Long-Term Self-Improvement Plan

_Last updated: 2025-07-18_

## 1. Purpose
This document is the **source of truth** for how SelfCoder will continuously
improve itself until a human declares it “powerful enough”.  It must be loaded
into the context every iteration (seed.py already reads all *.md* files), so the
agent always remembers its strategy, architecture and next steps.

## 2. Guiding Principles
1. **Safety first** – never modify `goal.md` or `.env`.
2. **Small, Reversible Steps** – prefer many tiny iterations over one gigantic
   change; every iteration must be runnable.
3. **Persistent Memory in Git** – long-term knowledge is stored in Markdown or
   JSON files inside `docs/` or `memory/`.  These are automatically included in
   the next context window.
4. **Measure & Evaluate** – every change should ideally include a test or metric
   that shows improvement (speed, capability, lower token usage, etc.).
5. **Human Time is Expensive** – only ask for `human_help` when absolutely
   necessary (e.g., package installation outside sandbox).

## 3. Architectural Roadmap
Phase 0  (👈 **current**)
• Establish long-term memory docs (this file, backlog).
• Enhance the system prompt with reflection instructions.

Phase 1 – Automated Unit-Testing Harness
• Add a `tests/` folder and simple pytest runner executed after each
  modification.
• Fail the iteration (skip applying changes) if tests regress.

Phase 2 – Self-Reflection & Scoring
• After code generation, run a second “critic” call to the LLM that reviews the
  diff and predicts impact.
• Store reflection notes in `memory/reflections/`.

Phase 3 – Tooling Layer
• Implement a small tools API (filesystem search, regex-replace, run shell
  commands in sandbox).
• Expose those tools to the LLM via function-calling through `openai`.

Phase 4 – Vector Memory & Retrieval
• Save code snippets / docs into a local embedding store (e.g.,
  `chromadb-lite`).  Retrieve relevant chunks for the next context.

Phase 5 – Meta-Learning
• Automatically analyse past iterations to find patterns of success/failure and
  adjust prompt weights.

## 4. Immediate Next-Step Checklist
- [x] Create long-term plan (this file).
- [x] Create backlog of concrete tasks.
- [ ] Implement pytest harness skeleton.
- [ ] Teach agent to run tests after edits.

See `docs/BACKLOG.md` for granular issues.

## 5. Evaluation Criteria for “Powerful Enough”
1. Can reliably modify multi-file Python projects with <1% syntax errors.
2. Has automated regression tests and rarely breaks them.
3. Maintains and uses long-term memory across >10 iterations.
4. Demonstrates ability to add non-trivial new features autonomously.
5. Human reviewer subjectively deems it competent to start the SAAS goal.
