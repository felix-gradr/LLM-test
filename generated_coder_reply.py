from pathlib import Path
import textwrap

# Determine repository root (directory containing this script, assuming coder.py is here)
_ROOT = Path(__file__).resolve().parent

# Path to the stub module
stub_path = _ROOT / "llm_utils.py"

# Create the stub only if it doesn't already exist
if not stub_path.exists():
    stub_code = textwrap.dedent(
        '''
        """
        Stub implementation of `llm_utils` used when the real LLM backend is
        unavailable.  It satisfies the import (`from llm_utils import chat_completion`)
        and provides a minimal `chat_completion` function that always returns
        a harmless, no-op Python code string.

        The goal is to keep the rest of the codebase running in offline / test
        environments without introducing non-standard-library dependencies.
        """

        from typing import List, Dict

        def chat_completion(messages: List[Dict[str, str]], preferred_model: str | None = None) -> str:
            """
            Very small stub that returns a no-op Python snippet.

            Parameters
            ----------
            messages : list[dict[str, str]]
                Chat messages passed by the caller.  Only used for basic logging.
            preferred_model : str | None
                Ignored in this stub.

            Returns
            -------
            str
                Python source code to be executed by the caller.  The code does
                nothing except print a diagnostic line, ensuring that execution
                continues without side effects.
            """
            # Extract last user message length for diagnostic purposes
            user_msg_len = 0
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_msg_len = len(msg.get("content", ""))
                    break

            # Produce a minimal, self-contained Python snippet
            return (
                "print("
                f"'[stub chat_completion] model={preferred_model} "
                f"user_msg_len={user_msg_len}')"
            )
        '''
    )
    stub_path.write_text(stub_code, encoding='utf-8')