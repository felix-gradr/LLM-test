# SelfCoder – Living Roadmap
This file acts as the **single source of truth** for what the agent is doing, why, and what
comes next. It is structured so that *any* incoming LLM request (whether o4-mini or o3)
can quickly load this file and know where to begin.

> Last updated: 2025-07-19 00:43 UTC

---

## 0. Guiding Principles
1. Keep the **immutable Goal** from goal.md in focus at all times.
2. Always prefer **automation over manual human input**. Humans are expensive.
3. Make iterative, **reversible** file mutations (use file_editor helpers).
4. Off-load cheap heuristics & pattern-matching tasks to `o4-mini`; reserve
   deep reasoning and multi-step planning for `o3-ver1`.
5. Persist memories & decisions so the agent never re-learns solved problems.

---

## 1. Architectural Overview
• **root.py** – entrypoint launched by the human each iteration.  
• **llm_helper.py** – thin wrappers around Azure OpenAI.  
• **file_editor.py** – granular utilities for code modifications.  
• **memory.py** – JSONL memory store with trimming logic.  
• **plan.md** – *this* living roadmap.  
• (future) **orchestrator.py** – hierarchical agent that chains model calls.  

---

## 2. Milestones & Status
| # | Milestone | Owner | Status | Notes |
|---|-----------|-------|--------|-------|
| M1 | Persistent memory                 | done | `memory.py` implemented |
| M2 | Granular file editing             | done | `file_editor.py` ready  |
| M3 | Expand roadmap (*you are here*)   | self | in-progress |
| M4 | Chain-of-LLMs orchestration       | self | queued |
| M5 | Automated test & lint pipeline    | self | backlog |
| M6 | Plugin system for specialised agents | self | backlog |

---

## 3. Current Sprint (M3 ➜ M4)
1. **Expand roadmap (this file) so new LLM calls have immediate context.**
2. **Design & scaffold an `orchestrator` module**:
   - `LightAgent` – uses `o4-mini` for inexpensive tasks (grep, summarise).
   - `HeavyAgent` – wraps `o3-ver1` for complex reasoning.
   - Simple task-router that decides which agent to invoke.
3. Refactor `root.py` to delegate to the orchestrator rather than calling
   `AzureOpenAI` directly.
4. Add unit tests for the router to ensure deterministic routing rules.

---

## 4. Backlog
• Synthetic test-suite generation for regression safety.  
• Automatic semantic-versioning & changelog updates.  
• Git-style diff visualisation between iterations.  
• CI integration (GitHub Actions) – will require human setup.  

---

## 5. Decision Log (chronological)
- [2025-07-19] Created `file_editor.py` and basic `llm_helper.py`.
- [2025-07-19 00:43 UTC] Overhauled `plan.md` with detailed roadmap and milestones.

---

## 6. How To Contribute (for future agents/humans)
1. **Read this file first** – update the roadmap *before* coding.
2. Use `file_editor` helpers; avoid blind overwrite of whole files.
3. After successful changes:
   - Update the *Decision Log* section above.
   - Bump milestone status if applicable.
