"""Helpers for routing lightweight LLM requests.

`LOCAL_THRESHOLD` determines when a tick can be handled by a local
"echo" model rather than being queued for a remote service.
"""

from __future__ import annotations

import asyncio
import os

import httpx

# When the computed confidence falls below this threshold the tick can be
# handled locally via :func:`call_local_echo`.
LOCAL_THRESHOLD: float = float(os.getenv("LOCAL_THRESHOLD", "0.6"))


def call_local_echo(prompt: str) -> str:
    """Send ``prompt`` to the MCP2 EchoNudge endpoint.

    Falls back to a deterministic echo when the service is unreachable.
    """

    async def _post() -> str:
        headers = {}
        api_key = os.getenv("MCP2_API_KEY")
        if api_key:
            headers = {
                "X-API-Key": api_key,
                "Authorization": f"Bearer {api_key}",
            }
        base = os.getenv("MCP2_BASE", "http://localhost:8002")
        async with httpx.AsyncClient(base_url=base, timeout=30) as client:
            resp = await client.post("/llm/echonudge", json={"prompt": prompt}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result")
        return str(result) if result is not None else ""

    try:
        return asyncio.run(_post())
    except Exception:
        return f"echo: {prompt}"


__all__ = ["LOCAL_THRESHOLD", "call_local_echo"]

