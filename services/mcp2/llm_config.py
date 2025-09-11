"""Helpers for routing lightweight LLM requests.

`LOCAL_THRESHOLD` determines when a tick can be handled by a local
"echo" model rather than being queued for a remote service.
"""

from __future__ import annotations

import os

# When the computed confidence falls below this threshold the tick can be
# handled locally via :func:`call_local_echo`.
LOCAL_THRESHOLD: float = float(os.getenv("LOCAL_THRESHOLD", "0.6"))


def call_local_echo(prompt: str) -> str:
    """Return a deterministic local response for ``prompt``.

    The real system may hook into a lightweight local model.  For tests and
    development this simply echoes the prompt.
    """

    return f"echo: {prompt}"


__all__ = ["LOCAL_THRESHOLD", "call_local_echo"]

