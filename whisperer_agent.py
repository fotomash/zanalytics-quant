"""Lightweight proxy for the Whisperer MCP service.

This FastAPI application forwards incoming trading state objects to a remote
Whisperer MCP backend.  The backend URL is configured via the ``MCP_HOST``
environment variable, replacing the deprecated ``WHISPERER_BACKEND`` setting.

Redis support is optional; if the ``redis`` package is not installed or the
service is unavailable, ``/cluster_narrate`` will return a helpful error rather
than failing at import time.

In addition to the ``/mcp`` passthrough, the service exposes ``/cluster_narrate``
which initialises Redis (when available) and Qdrant clients then delegates to
``WhisperEngine.cluster_narrator`` to produce a narrative and recommendation for
the supplied cluster identifier.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:  # Redis is optional
    import redis  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully
    redis = None  # type: ignore

from services.vectorization_service.brown_vector_store_integration import (
    BrownVectorPipeline,
)
from whisper_engine import State, WhisperEngine

# Default MCP endpoint if the environment variable is unset.
MCP_HOST = os.getenv("MCP_HOST", "https://mcp2.analytics.org/api/v1/whisperer/exec")

# Optional endpoints for cluster queries.
CLUSTER_API = os.getenv("CLUSTER_API")
VECTOR_SEARCH_URL = os.getenv("VECTOR_SEARCH_URL")

app = FastAPI(title="Whisperer MCP")


class ClusterPayload(BaseModel):
    """Request body for ``/cluster_narrate`` containing the top cluster."""

    top_cluster: dict


@app.post("/mcp")
async def mcp(state: State):
    """Forward the trading state to the configured MCP host."""
    async with httpx.AsyncClient() as client:
        response = await client.post(MCP_HOST, json=asdict(state))
        response.raise_for_status()
        return response.json()


async def _fetch_cluster_from_dashboard(date: str) -> Optional[Any]:
    """Fetch RSI divergence cluster data from the dashboard service."""
    if not CLUSTER_API:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{CLUSTER_API.rstrip('/')}/rsi/divergence", params={"date": date}
            )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                if "top_cluster" in data:
                    return data["top_cluster"]
                clusters = data.get("clusters")
                if isinstance(clusters, list) and clusters:
                    return clusters[0]
        return None
    except Exception:
        return None


async def _fetch_cluster_from_vector_store(date: str) -> Optional[Any]:
    """Query vector store for RSI divergence cluster information."""
    if not VECTOR_SEARCH_URL:
        return None
    payload = {"query": f"Top RSI divergence cluster on {date}", "k": 1}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(VECTOR_SEARCH_URL, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            matches = data.get("matches")
            if isinstance(matches, list) and matches:
                top = matches[0]
                if isinstance(top, dict):
                    return top.get("payload", top)
                return top
        return None
    except Exception:
        return None


class ClusterNarrateRequest(BaseModel):
    cluster: Dict[str, Any]


@app.post("/cluster_narrate")
async def cluster_narrate(payload: ClusterNarrateRequest):
    """Return a narrative for a provided cluster.

    The endpoint initialises Redis and :class:`BrownVectorPipeline` clients and
    delegates to :func:`WhisperEngine.cluster_narrator`.  Callers must provide a
    cluster object containing an ``embedding`` field which is used with
    ``search_similar_clusters``.
    """

    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="Redis support is not installed; cluster narration is unavailable.",
        )
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )
    except Exception as exc:  # pragma: no cover - network failure
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {exc}")
    qdrant = BrownVectorPipeline()
    engine = WhisperEngine({})
    return engine.cluster_narrator(payload.cluster, r, qdrant)


@app.get("/rsi-divergence-cluster")
async def rsi_divergence_cluster(date: str):
    """Return the top RSI divergence cluster for ``date``.

    The function first attempts to retrieve clustering data from the dashboard
    service. If unavailable, it falls back to querying an external vector
    store. Both data sources are optional; if neither is configured or returns
    a result, ``cluster`` will be ``None``.
    """
    cluster = await _fetch_cluster_from_dashboard(date)
    if cluster is None:
        cluster = await _fetch_cluster_from_vector_store(date)
    return {"date": date, "cluster": cluster}


@app.post("/cluster_narrate")
async def cluster_narrate(payload: ClusterPayload) -> dict:
    """Return a narrative for the supplied cluster."""

    engine = WhisperEngine({})

    try:
        import redis as _redis
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Redis support is not installed; cluster narration is unavailable.",
        )
    from qdrant_client import QdrantClient

    try:
        redis_client = _redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )
    except Exception as exc:  # pragma: no cover - network failure
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {exc}")

    qdrant_client: Any = None
    try:

        class QdrantAdapter:
            def __init__(self) -> None:
                self._client = QdrantClient(
                    url=os.getenv("QDRANT_URL"),
                    api_key=os.getenv("QDRANT_API_KEY"),
                )
                self._collection = os.getenv("QDRANT_COLLECTION", "clusters")

            def search(self, embedding, top_k: int = 3):
                try:
                    return self._client.search(
                        collection_name=self._collection,
                        query_vector=embedding,
                        limit=top_k,
                    )
                except Exception:
                    return []

        qdrant_client = QdrantAdapter()
    except Exception:
        qdrant_client = None

    return engine.cluster_narrator(payload.top_cluster, redis_client, qdrant_client)
