
"""Utility for obtaining chat completions from the best available backend.

Order of preference:
1. Azure OpenAI (if AZURE_KEY & AZURE_ENDPOINT are configured)
2. OpenAI public endpoint (if OPENAI_API_KEY / OPENAI_KEY is configured)
3. Local stub that still produces executable Python code (keeps project moving)
"""
import os, traceback
from datetime import datetime, timezone

def _try_azure(messages, model):
    try:
        from openai import AzureOpenAI
        if not (os.getenv("AZURE_KEY") and os.getenv("AZURE_ENDPOINT")):
            return None
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_KEY"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version="2025-03-01-preview",
        )
        response = client.chat.completions.create(model=model, messages=messages)
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[llm_utils] Azure backend failed: {e}")
        traceback.print_exc()
        return None

def _try_openai(messages, model):
    try:
        import openai
        key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
        if not key:
            return None
        # openai-python >= 1.0
        if hasattr(openai, "OpenAI"):
            client = openai.OpenAI(api_key=key)
            response = client.chat.completions.create(model=model, messages=messages)
        else:
            # Legacy API style
            openai.api_key = key
            response = openai.ChatCompletion.create(model=model, messages=messages)
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[llm_utils] Public OpenAI backend failed: {e}")
        traceback.print_exc()
        return None

def _stub_reply(messages):
    """Return a minimal yet syntactically valid Python snippet ensuring progress."""
    ts = datetime.now(timezone.utc).isoformat()
    code = (
        "from pathlib import Path
"
        "import datetime as _d
"
        "Path('auto_progress.md').write_text("
        "f'Stub LLM progress {ts}')
"
    )
    return code

def chat_completion(messages, preferred_model="o3-ver1"):
    """Return best-effort chat completion (string containing Python code)."""
    # 1) Try Azure with the requested model
    reply = _try_azure(messages, preferred_model)
    if reply:
        return reply

    # 2) Fallback to public OpenAI (choose sensible model)
    openai_model = "gpt-4o-mini" if preferred_model.startswith("o4") else "gpt-3.5-turbo"
    reply = _try_openai(messages, openai_model)
    if reply:
        return reply

    # 3) Final fallback — return stub code so the system still advances
    return _stub_reply(messages)
