# 🗺️  Self-Improvement Plan for SelfCoder

This document is **the living roadmap** for empowering the agent.  Read the *Next-up* section at the start of every iteration and update it when tasks are completed or priorities change.

---

## 0. Principles
1. **Small, safe steps** – Prefer patches and isolated modules.
2. **Continuous learning** – Capture insights in `memory.json` after each run.
3. **Automate the mundane** – Delegate low-level tasks to lighter models.
4. **Keep the human out of the loop** whenever possible; request help only for actions outside the sandbox (e.g., package installation).

---

## 1. Milestones
1. ✅  Baseline: persistent memory + single LLM loop (already exists)
2. 🔄  Better prompt & explicit plan (this file, today)
3. ⏭️  Modular codebase (split `root.py` into `agent.py`, `io_utils.py`, etc.)
4. ⏭️  Multi-LLM orchestration
5. ⏭️  Automated tests / self-evaluation harness

---

## 2. Next-up Tasks (work on these **in order**)
1. **Refactor `root.py`**
   • Move memory helpers to `memory_utils.py`
   • Create `agent_runner.py` that exposes `agent_step`
2. **Introduce light-weight analysis agent**
   • New module `agents/reader.py` (model: `o4-mini`) – returns concise code summaries
3. **Chain calls**
   • `o4-mini` proposes patches  → `o3-ver1` validates & finalises
4. **Repo tidying**
   • Add `.gitattributes` to normalise line endings
   • Ensure requirements list is clean (current file appears corrupted)
5. **Write minimal unit tests** (pytest) for memory helpers

---

## 3. Stretch Ideas
- Add semantic search over code history
- Auto-bump package versions via Dependabot-like workflow

---

## 4. Changelog
- 2025-07-19 – Created initial `plan.md`, outlined milestones & immediate tasks.
