# Persistent Memory for SelfCoder

This file stores long-term memory that survives across iterations. Keep entries concise and append new information as needed so the most recent and relevant knowledge appears near the top.

---
## 2025-07-18 – Roadmap & Idea Backlog
1. Added `docs/roadmap.md`, `docs/ideas.md`, and `docs/stack.md` outlining phased plan, candidate SaaS concepts, and preferred technology stack.
2. Updated `seed.py` so the agent ignores `.venv`, `venv`, and `__pycache__` directories when reading the repository, reducing prompt bloat.
3. Next tasks:
   - Score & shortlist SaaS ideas, choose one to pursue.
   - Draft detailed product spec & validation experiments.
   - Establish basic CI pipeline (linting, tests) and code-style tooling.

---
## 2025-07-18 – Initial Bootstrapping
1. Goal: Build a SaaS that earns **≥ $1,000/month**.
2. Current phase: Laying infrastructure & planning – _do **not** jump straight into coding the SaaS._
3. Key decisions:
   - Implement a simple `memory.md` file for persistence between steps (done in this commit).
   - Inject memory into the agent prompt (implemented by editing `seed.py`).
   - Next tasks will focus on writing a high-level roadmap and evaluating potential SaaS ideas.

### Next Planned Steps (superseded by newer entry above)
- [ ] Create `docs/roadmap.md` outlining phased plan (research, validation, MVP, marketing, scaling).
- [ ] Compile a backlog of candidate SaaS ideas with quick TAM / competition analysis.
- [ ] Decide on tooling stack and repo structure for future service code (backend, frontend, infra).
