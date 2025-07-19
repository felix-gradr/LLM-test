"""llm_helper.py
Utility wrappers around Azure OpenAI chat completions.

Why this exists
---------------
1. Centralises configuration & invocation logic so other modules don't have
   to duplicate boilerplate.
2. Makes it trivial to route lightweight queries to `o4-mini` while keeping
   heavyweight reasoning on `o3-ver1`.
3. Encapsulates retry-with-backoff logic for better robustness.

Usage
-----
    from llm_helper import ask_o4, ask_o3

    answer = ask_o4("Summarise this file ...")

The returned content is always the stripped assistant message string.

NOTE: Environment variables `AZURE_KEY` and `AZURE_ENDPOINT` must be set.
"""

from __future__ import annotations

import os
import time
from typing import List, Dict, Literal

from openai import AzureOpenAI
from openai._exceptions import OpenAIError

__all__ = [
    "call_chat",
    "ask_o4",
    "ask_o3",
]

_DEFAULT_API_VERSION = "2025-03-01-preview"
_MAX_RETRIES = 3
_BACKOFF_SECONDS = 2.0


def _get_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.getenv("AZURE_KEY"),
        azure_endpoint=os.getenv("AZURE_ENDPOINT"),
        api_version=_DEFAULT_API_VERSION,
    )


def call_chat(
    messages: List[Dict[str, str]],
    model: Literal["o4-mini", "o3-ver1"] = "o4-mini",
    temperature: float = 0.0,
) -> str:
    """Low-level helper to call Azure OpenAI chat completions.

    Implements basic exponential back-off retries to improve reliability.
    """
    client = _get_client()
    last_err = None
    temperature = 1 # Only a temperature of 1 is supported by o4-mini AND o3-ver1 models. //Human
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except OpenAIError as e:
            last_err = e
            if attempt == _MAX_RETRIES:
                raise
            time.sleep(_BACKOFF_SECONDS * attempt)
    # This point is only reached if retries exhausted without re-raising.
    raise RuntimeError(f"Chat completion failed: {last_err}") from last_err


# ------------------------------------------------------------------ #
#  High-level single-prompt helpers
# ------------------------------------------------------------------ #

_SYS_O4 = {"role": "system", "content": "You are a lightweight helpful assistant."}
_SYS_O3 = {"role": "system", "content": "You are a powerful reasoning agent."}


def ask_o4(user_prompt: str, *, temperature: float = 0.2) -> str:
    """Send *user_prompt* to the lightweight `o4-mini` model."""
    messages = [_SYS_O4, {"role": "user", "content": user_prompt}]
    return call_chat(messages, model="o4-mini", temperature=temperature)


def ask_o3(user_prompt: str, *, temperature: float = 0.0) -> str:
    """Send *user_prompt* to the heavyweight `o3-ver1` model."""
    messages = [_SYS_O3, {"role": "user", "content": user_prompt}]
    return call_chat(messages, model="o3-ver1", temperature=temperature)
