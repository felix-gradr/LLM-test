from __future__ import annotations

"""Loop-protection utilities for SelfCoder.

The purpose of this helper is to detect *identical* action payloads across
consecutive iterations.  If the agent keeps proposing exactly the same JSON
(e.g. because the LLM got stuck), we can short-circuit the cycle early and thus
fulfil the *Current Sub-goal* requirement of avoiding infinite loops.

The implementation purposefully has **zero** external dependencies and is
lightweight so that importing it inside *root.py* adds negligible risk.

Design goals
============
1. No modification of the memory format – we only **read** the existing
   structured JSONL or legacy flat log.
2. Graceful degradation – if anything goes wrong, simply return *False* so we
   never block progress because of a bug here.
3. Minimal footprint – a single file, pure stdlib.
"""

from pathlib import Path
import json
from typing import Any, Dict

try:
    # Optional dependency – *root.py* may run without the structured manager
    from memory_manager import Memory  # type: ignore
except Exception:
    Memory = None  # noqa: N816 (constant-like alias)

# ---------------------------------------------------------------------------
# Helper class (namespace-style)
# ---------------------------------------------------------------------------
class LoopProtector:
    """Static helpers to detect and mitigate repeated identical actions."""

    _LEGACY_MEMORY_PATH: Path = Path(__file__).parent / "memory.log"

    # ----------------------------- Public API -----------------------------
    @staticmethod
    def is_redundant(actions: Dict[str, Any]) -> bool:  # noqa: D401 – imperative style
        """Return *True* if *actions* exactly matches the last stored action.

        The comparison is performed on a *stable* JSON representation (keys
        sorted) so re-ordering inside dictionaries does not matter.
        """
        try:
            last_raw = LoopProtector._last_action_raw()
            if last_raw is None:
                return False
            last_obj = json.loads(last_raw)
            return LoopProtector._stable(last_obj) == LoopProtector._stable(actions)
        except Exception:
            # Any failure -> assume *not* redundant to avoid false positives
            return False

    # --------------------------- Internal helpers -------------------------
    @staticmethod
    def _stable(obj: Dict[str, Any]) -> str:
        """Return canonical JSON (sorted keys, no whitespace)."""
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _last_action_raw() -> str | None:
        """Fetch the *raw* JSON string of the most recent 'action' record."""
        # Preferred: structured memory
        if Memory is not None:
            try:
                for rec in reversed(Memory.load()):
                    if rec.get("type") == "action":
                        return rec.get("content")  # type: ignore[return-value]
            except Exception:
                pass  # fall back to legacy

        # Legacy fallback – iterate the flat log in reverse
        path = LoopProtector._LEGACY_MEMORY_PATH
        if not path.is_file():
            return None
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for ln in reversed(lines):
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    candidate = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and "action" in candidate:
                    return ln
        except Exception:
            pass  # silent – better be permissive
        return None
