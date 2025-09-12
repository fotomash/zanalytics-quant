"""Lightweight proxy for the Whisperer MCP service.

This FastAPI application forwards incoming trading state objects to a remote
Whisperer MCP backend.  The backend URL is configured via the ``MCP_HOST``
environment variable, replacing the deprecated ``WHISPERER_BACKEND`` setting.
"""

from __future__ import annotations

import os
from dataclasses import asdict

import httpx
from fastapi import FastAPI

from whisper_engine import State

# Default MCP endpoint if the environment variable is unset.
MCP_HOST = os.getenv(
    "MCP_HOST", "https://mcp2.analytics.org/api/v1/whisperer/exec"
)

app = FastAPI(title="Whisperer MCP")


@app.post("/mcp")
async def mcp(state: State):
    """Forward the trading state to the configured MCP host."""
    async with httpx.AsyncClient() as client:
        response = await client.post(MCP_HOST, json=asdict(state))
        response.raise_for_status()
        return response.json()

