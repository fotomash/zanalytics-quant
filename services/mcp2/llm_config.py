import os
import logging
from typing import Any

import requests
import openai

LOCAL_ECHO_URL = "http://localhost:11434/api/generate"
WHISPERER_URL = "https://api.openai.com/v1/chat/completions"
LOCAL_THRESHOLD = float(os.getenv("LOCAL_THRESHOLD", "0.6"))

logger = logging.getLogger(__name__)


def call_whisperer(prompt: str) -> str:
    """Send ``prompt`` to OpenAI's Whisperer model and return the response."""
    openai.api_key = os.getenv("OPENAI_API_KEY", "")
    resp: Any = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp["choices"][0]["message"]["content"]


def call_local_echo(prompt: str) -> str:
    """Try local echo service; fallback to Whisperer on failure."""
    try:
        r = requests.post(
            LOCAL_ECHO_URL,
            json={"model": "llama3", "prompt": prompt},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        # Try common keys for model output
        content = (
            data.get("response")
            or data.get("choices", [{}])[0].get("text")
            or ""
        )
        if content:
            return content
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("Local echo failed: %s", exc)
    return call_whisperer(prompt)


__all__ = [
    "LOCAL_ECHO_URL",
    "WHISPERER_URL",
    "LOCAL_THRESHOLD",
    "call_local_echo",
    "call_whisperer",
]
