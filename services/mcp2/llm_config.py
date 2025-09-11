"""Helpers for routing lightweight LLM requests.

`LOCAL_THRESHOLD` determines when a tick can be handled by a local
"echo" model versus being queued for a remote Whisperer service.
"""

from __future__ import annotations

import os

LOCAL_THRESHOLD: float = float(os.getenv("LOCAL_THRESHOLD", "0.6"))


def call_local_echo(prompt: str) -> str:
    """Return a deterministic local response for `prompt`.

    The real system may hook into a lightweight local model. For tests and
    development this simply echoes the prompt.
    """

    return f"echo: {prompt}"
