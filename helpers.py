
from __future__ import annotations
import fnmatch
from pathlib import Path
from typing import Dict
from error_logger import log_error

# Extensions considered source code / text (edit as needed)
CODE_EXTENSIONS = {'.py', '.txt', '.md', '.json', '.yaml', '.yml', '.toml'}

def _read_gitignore(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    patterns: list[str] = []
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns

def _is_ignored(path: Path, root: Path, ignore_patterns: list[str]) -> bool:
    rel_path = path.relative_to(root).as_posix()
    for pattern in ignore_patterns:
        if pattern.endswith("/"):  # dir pattern
            if rel_path.startswith(pattern) or fnmatch.fnmatch(rel_path, pattern + "*"):
                return True
        elif "/" not in pattern:  # filename pattern e.g. *.log
            if fnmatch.fnmatch(path.name, pattern):
                return True
        else:  # glob with slash
            if fnmatch.fnmatch(rel_path, pattern):
                return True
    return False

def read_codebase(root: Path, max_chars: int = 120_000) -> str:
    """Return a truncated snapshot of the repository for prompt context"""
    files: Dict[str, str] = {}
    ignore_patterns = _read_gitignore(root)
    for path in root.rglob("*"):
        if path.is_dir() or _is_ignored(path, root, ignore_patterns):
            continue
        if path.suffix in CODE_EXTENSIONS and path.is_file():
            try:
                files[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
            except Exception as exc:  # pragma: no cover
                log_error(f"helpers.read_codebase: cannot read {path}", exc)
    joined = "\n".join(f"## {name}\n{content}" for name, content in files.items())
    return joined[:max_chars]
