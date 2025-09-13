"""Lightweight proxy for the Whisperer MCP service.

This FastAPI application forwards incoming trading state objects to a remote
Whisperer MCP backend.  The backend URL is configured via the ``MCP_HOST``
environment variable, replacing the deprecated ``WHISPERER_BACKEND`` setting.

In addition to the ``/mcp`` passthrough, the service exposes ``/cluster_narrate``
which initialises Redis and Qdrant clients then delegates to
``WhisperEngine.cluster_narrator`` to produce a narrative and recommendation for
the supplied cluster identifier.
"""

from __future__ import annotations

import os
from dataclasses import asdict

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from whisper_engine import State, WhisperEngine

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


class ClusterRequest(BaseModel):
    """Payload identifying the top cluster to narrate."""

    top_cluster: str


@app.post("/cluster_narrate")
async def cluster_narrate(payload: ClusterRequest):
    """Return a narrative and recommendation for ``payload.top_cluster``."""

    import redis
    from qdrant_client import QdrantClient

    top_cluster = payload.top_cluster

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        r = redis.Redis.from_url(redis_url, decode_responses=True)
    else:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    engine = WhisperEngine({})
    return engine.cluster_narrator(top_cluster, r, qdrant)

