# Backlog – Concrete Improvement Tasks

_The agent should pick tasks from here in future iterations._

Priority legend: 🟥 Urgent | 🟧 High | 🟨 Medium | 🟩 Low

| ID | Priority | Title | Status |
|----|----------|-------|--------|
| B1 | 🟧 | Add pytest harness and a simple always-pass test to ensure CI path works. | TODO |
| B2 | 🟧 | Update `seed.py` to automatically run tests (if `pytest` available) after applying LLM changes. | TODO |
| B3 | 🟨 | Add reflection step: second LLM call that critiques the first response; store in `memory/reflections/`. | TODO |
| B4 | 🟨 | Implement `tools/fs_find.py` utility and expose it via function-calling. | TODO |
| B5 | 🟩 | Create embedding memory with `chromadb` (or fallback JSON). | TODO |
| B6 | 🟩 | Token-usage logger to track cost over iterations. | TODO |
