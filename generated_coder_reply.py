from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).parent

target = ROOT / "coder.py"
code = target.read_text(encoding="utf-8")

# 1. Insert/replace _cleanup_junk function and call
cleanup_func = textwrap.dedent("""\
    def _cleanup_junk() -> None:
        \"\"\"Remove transient files and trim logs to keep the repo tidy.

        1. Delete one-time seed.txt (if present)
        2. Trim coder.log to the last 300 lines
        3. Rotate generated_coder_reply.py into generated_backups/ (keep 3 most recent)
        \"\"\"
        import time, shutil

        # (1) Remove seed.txt on first run
        seed = _ROOT / "seed.txt"
        if seed.exists():
            try:
                seed.unlink()
            except Exception:
                pass

        # (2) Trim coder.log
        log = _ROOT / "coder.log"
        if log.exists():
            try:
                lines = log.read_text(encoding="utf-8", errors="ignore").splitlines()
                max_lines = 300
                if len(lines) > max_lines:
                    log.write_text("\\n".join(lines[-max_lines:]), encoding="utf-8")
            except Exception:
                pass

        # (3) Rotate generated_coder_reply.py
        gen = _ROOT / "generated_coder_reply.py"
        if gen.exists():
            try:
                backup_dir = _ROOT / "generated_backups"
                backup_dir.mkdir(exist_ok=True)
                ts = int(time.time())
                gen.replace(backup_dir / f"coder_reply_{ts}.py")
                backups = sorted(backup_dir.glob("coder_reply_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
                for p in backups[3:]:
                    try:
                        p.unlink()
                    except Exception:
                        pass
            except Exception:
                pass
""")

if "_cleanup_junk(" not in code:
    # place cleanup function after _ROOT definition
    pattern = r"^_ROOT\s*=\s*Path\(__file__\)\.parent"
    m = re.search(pattern, code, flags=re.MULTILINE)
    if m:
        insert_at = m.end()
        code = code[:insert_at] + "\n\n" + cleanup_func + "\n\n" + code[insert_at:]

# Ensure _cleanup_junk() is invoked at import time (after _ROOT exists)
if "_cleanup_junk()" not in code:
    pattern = r"^_ROOT\s*=\s*Path\(__file__\)\.parent"
    m = re.search(pattern, code, flags=re.MULTILINE)
    if m:
        # find the end of the line to insert call right after
        insert_at = code.find("\n", m.end()) + 1
        code = code[:insert_at] + "_cleanup_junk()\n" + code[insert_at:]

# 2. Replace _snapshot_codebase with a leaner version
snapshot_func = textwrap.dedent("""\
    def _snapshot_codebase(max_chars: int = 6000, per_file_char_limit: int = 2000) -> str:
        \"\"\"Return a truncated snapshot of the codebase.

        - Skips virtual-env folders and backup directories
        - Skips files larger than per_file_char_limit
        - Truncates accumulated snapshot to max_chars
        \"\"\"
        parts = []
        for p in sorted(_ROOT.rglob("*.py")):
            if any(x in p.parts for x in ("venv", ".venv", "generated_backups")):
                continue
            try:
                content = p.read_text()
            except Exception:
                continue
            if len(content) > per_file_char_limit:
                continue
            parts.append(f"## {p}\\n{content}")
            if sum(len(s) for s in parts) >= max_chars:
                break
        snapshot = "\\n".join(parts)
        return snapshot[:max_chars]
""")

code = re.sub(
    r"def _snapshot_codebase\([^\n]*\n(?:[^\\n]*\n)+?^\s*return[^\n]*",
    snapshot_func.rstrip(),
    code,
    flags=re.MULTILINE,
)

# Write patched file
target.write_text(code, encoding="utf-8")