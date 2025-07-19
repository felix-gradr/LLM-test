from pathlib import Path, PurePath
import datetime as _dt
import shutil
import textwrap
import re

_ROOT = Path(__file__).parent
coder_path = _ROOT / "coder.py"
code = coder_path.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# 1) Inject a backup routine if not present
# ---------------------------------------------------------------------------
if "_create_backup(" not in code:
    backup_func = textwrap.dedent(
        """
        def _create_backup() -> Path:
            \"\"\"Create a timestamped backup of all .py files in the repo.

            Returns the path to the created backup directory.
            \"\"\"
            ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            backup_dir = _ROOT / ".backups" / ts
            backup_dir.mkdir(parents=True, exist_ok=True)
            for p in _ROOT.rglob("*.py"):
                if any(x in p.parts for x in ("venv", ".venv", "__pycache__", ".backups")):
                    continue
                rel = p.relative_to(_ROOT)
                dest = backup_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(p, dest)
                except Exception:
                    # Best-effort backup; continue on failure
                    continue
            return backup_dir
        """
    ).lstrip("\n")
    # Insert just after imports
    pattern = re.compile(r"(from llm_utils import chat_completion\s*)")
    code = pattern.sub(r"\1\n" + backup_func, code, count=1)

# ---------------------------------------------------------------------------
# 2) Amend apply_task to call _create_backup and exec in restricted sandbox
# ---------------------------------------------------------------------------
if "_create_backup()" not in code or "__coder_exec__" in code and "__safe_globals" not in code:
    lines = code.splitlines()
    new_lines = []
    inside_apply = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("def apply_task("):
            inside_apply = True
        if inside_apply and stripped.startswith("messages = ["):
            # Directly before building messages, ensure backup call
            indent = " " * (len(line) - len(stripped))
            new_lines.append(f"{indent}_create_backup()  # safety: backup before modifications")
        if inside_apply and "exec(reply" in line and "__coder_exec__" in line:
            indent = line[:line.find("exec")]
            sandbox = (
                indent
                + "safe_builtins = {\n"
                + indent
                + "    k: __builtins__[k] for k in (\n"
                + indent
                + "        'print','len','range','enumerate','list','dict','set','int','float','str',\n"
                + indent
                + "        'bool','abs','min','max','sum','__import__'\n"
                + indent
                + "    ) if k in __builtins__\n"
                + indent
                + "}\n"
                + indent
                + "__safe_globals = {'__builtins__': safe_builtins, '__name__': '__coder_exec__'}\n"
                + indent
                + "exec(reply, __safe_globals)\n"
            )
            new_lines.append(sandbox)
            continue  # skip original exec line
        new_lines.append(line)
        # Detect end of function
        if inside_apply and stripped.startswith("return status"):
            inside_apply = False
    code = "\n".join(new_lines)

# ---------------------------------------------------------------------------
# 3) Write back changes (idempotent)
# ---------------------------------------------------------------------------
coder_path.write_text(code, encoding="utf-8")