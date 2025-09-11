from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def call_local_echo(prompt: str) -> str:
    """Send ``prompt`` to the local EchoNudge model.

    Falls back to a deterministic stub when the local service is unreachable.
    """
    url = os.getenv("LOCAL_ECHO_URL")
    if url:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"prompt": prompt}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("verdict") or data.get("response") or str(data)
        except Exception as exc:  # pragma: no cover - network failure
            logger.error("local echo request failed: %s", exc)
    return f"echo: {prompt}"


async def call_whisperer(prompt: str) -> str:
    """Send ``prompt`` to the Whisperer service.

    Reuses the HTTP API and returns a deterministic stub when offline.
    """
    url = os.getenv("WHISPERER_URL")
    if url:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"prompt": prompt}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("verdict") or data.get("response") or str(data)
        except Exception as exc:  # pragma: no cover - network failure
            logger.error("whisperer request failed: %s", exc)
    return f"whisperer: {prompt}"


__all__ = ["call_local_echo", "call_whisperer"]
