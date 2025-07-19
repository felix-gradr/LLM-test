from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).parent

def ensure_logging_utils():
    target = ROOT / "logging_utils.py"
    if target.exists():
        return
    code = textwrap.dedent("""
        \"\"\"Centralised logging utilities for the project.\"\"\"
        import logging
        from pathlib import Path

        def configure_logging(log_file: str = "app.log", level: int = logging.INFO) -> None:
            \"\"\"Initialise a basic logging setup if none exists yet.\"\"\"
            root_logger = logging.getLogger()
            if root_logger.handlers:
                # Already configured
                return

            log_path = Path(__file__).parent / log_file
            log_path.parent.mkdir(parents=True, exist_ok=True)

            fmt = logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setFormatter(fmt)
            root_logger.addHandler(fh)

            sh = logging.StreamHandler()
            sh.setFormatter(fmt)
            root_logger.addHandler(sh)

            root_logger.setLevel(level)
    """).strip() + "\n"
    target.write_text(code, encoding="utf-8")


def patch_file(path: Path, patches: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    original = text
    for pattern, replacement in patches:
        if re.search(pattern, text, flags=re.M):
            text = re.sub(pattern, replacement, text, flags=re.M)
    if text != original:
        path.write_text(text, encoding="utf-8")


def add_logging_to_coder():
    path = ROOT / "coder.py"
    if not path.exists():
        return

    # 1. Ensure imports + configuration at the top.
    import_patch_pattern = r"(^from pathlib import Path[^\n]*\n(?:[^\n]*\n)*?)"
    import_patch_repl = (
        "\\1import logging\nfrom logging_utils import configure_logging\n"
        "configure_logging()\nlogger = logging.getLogger(__name__)\n"
    )
    # 2. Record log in record_task
    record_patch_pattern = r"(def record_task\(.*?[\s\S]*?fp\.write\(.*?\))"
    record_patch_repl = "\\1\n    logger.info('Recorded task: %s', task)"
    # 3. Add logs in apply_task
    apply_start_pattern = r"(def apply_task\(.*?\):\n)(\s+\"\"\".*?\"\"\"[\s\S]*?messages = )"
    apply_start_repl = "\\1\\2\n    logger.info('Applying task: %s', task)"
    # 4. Log exception in apply_task
    apply_exc_pattern = r"(except Exception as e:\n\s+status = .*?\n)"
    apply_exc_repl = "\\1        logger.exception('Error executing generated code for task: %s', task)"
    # 5. Log completion
    apply_end_pattern = r"(writer?.*?status\)\n)"
    apply_end_repl = "\\1    logger.info(\"Task '%s' completed with status: %s\", task, status)\n"

    patch_file(path, [
        (import_patch_pattern, import_patch_repl),
        (record_patch_pattern, record_patch_repl),
        (apply_start_pattern, apply_start_repl),
        (apply_exc_pattern, apply_exc_repl),
        (apply_end_pattern, apply_end_repl),
    ])


def add_logging_to_fallback():
    path = ROOT / "fallback.py"
    if not path.exists():
        return

    # Insert logging import & configure at top (after future import line if present)
    import_block_pattern = r"(^from __future__ import[^\n]+\n)"
    import_block_repl = (
        "\\1\nimport logging\nfrom logging_utils import configure_logging\n"
        "configure_logging()\nlogger = logging.getLogger(__name__)\n"
    )
    patch_file(path, [(import_block_pattern, import_block_repl)])

    # Add a starting log line inside agent_step
    agent_step_start_pattern = r"(def agent_step\(.*?\):\n\s+\"\"\"[^\"]*\"\"\"\n)"
    agent_step_start_repl = "\\1    logger.info('agent_step started')\n"
    # Add exception logging inside agent_step where snapshot is built
    agent_step_try_pattern = r"(snapshot = read_codebase\(root\))"
    agent_step_try_repl = (
        "try:\n        \\1\n    except Exception:\n        logger.exception('Failed during read_codebase')\n        "
        "raise"
    )

    patch_file(path, [
        (agent_step_start_pattern, agent_step_start_repl),
        (agent_step_try_pattern, agent_step_try_repl),
    ])


def main():
    ensure_logging_utils()
    add_logging_to_coder()
    add_logging_to_fallback()


if __name__ == "__main__":
    main()