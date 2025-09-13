"""Utility functions for storing and searching cluster context.

This module provides helper functions that persist cluster-related context in
Redis and upsert corresponding embeddings to a Qdrant vector store. The
implementation relies on :class:`LLMRedisBridge` for Redis interactions and
:class:`BrownVectorPipeline` for Qdrant operations.

The vector store is configured via the ``QDRANT_URL`` and ``QDRANT_API_KEY``
environment variables. When these variables are missing or the backend is
unreachable, vector operations are silently skipped.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None  # type: ignore[assignment]

from llm_redis_bridge import LLMRedisBridge
from services.vectorization_service.brown_vector_store_integration import (
    BrownVectorPipeline,
)

__all__ = [
    "store_cluster_context",
    "fetch_cluster_context",
    "search_similar_clusters",
]

_redis_bridge: Optional[LLMRedisBridge] = None
_vector_pipeline: Optional[BrownVectorPipeline] = None


def _get_redis_bridge() -> Optional[LLMRedisBridge]:
    """Return a cached :class:`LLMRedisBridge` instance if available."""

    global _redis_bridge
    if redis is None:
        return None
    if _redis_bridge is None:
        try:
            client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True,
            )
            client.ping()
            _redis_bridge = LLMRedisBridge(client)
        except (
            Exception
        ):  # pragma: no cover - connection failures are environment specific
            _redis_bridge = None
    return _redis_bridge


def _get_vector_pipeline() -> Optional[BrownVectorPipeline]:
    """Return a cached :class:`BrownVectorPipeline` instance if available."""

    global _vector_pipeline
    if _vector_pipeline is None:
        try:
            _vector_pipeline = BrownVectorPipeline()
        except Exception:  # pragma: no cover - missing configuration or network errors
            _vector_pipeline = None
    return _vector_pipeline


def store_cluster_context(
    cluster_id: str,
    context: Dict[str, Any],
    embedding: Optional[List[float]] = None,
) -> None:
    """Persist ``context`` for ``cluster_id`` in Redis and optionally Qdrant.

    Parameters
    ----------
    cluster_id:
        Unique identifier for the cluster.
    context:
        Arbitrary context payload to store in Redis.
    embedding:
        Optional vector representation of the cluster context. When provided and
        a vector store is configured, the embedding is upserted using
        :class:`BrownVectorPipeline`.
    """

    bridge = _get_redis_bridge()
    if bridge is not None:
        try:
            bridge.redis.set(f"cluster:context:{cluster_id}", json.dumps(context))
        except Exception:  # pragma: no cover - Redis failures are environment specific
            pass

    if embedding is not None:
        pipeline = _get_vector_pipeline()
        if pipeline is not None:
            try:
                pipeline.upsert_vector(
                    cluster_id,
                    embedding,
                    {"cluster_id": cluster_id},
                )
            except Exception:  # pragma: no cover - network failures
                pass


def fetch_cluster_context(cluster_id: str) -> Dict[str, Any]:
    """Retrieve context previously stored for ``cluster_id``.

    Returns an empty dictionary when Redis is unavailable or the key does not
    exist.
    """

    bridge = _get_redis_bridge()
    if bridge is None:
        return {}
    try:
        data = bridge.redis.get(f"cluster:context:{cluster_id}")
        return json.loads(data) if data else {}
    except Exception:  # pragma: no cover - Redis failures are environment specific
        return {}


def search_similar_clusters(
    embedding: List[float],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Search the vector store for clusters similar to ``embedding``.

    Parameters
    ----------
    embedding:
        Vector representation to search against.
    top_k:
        Maximum number of results to return.

    Returns
    -------
    List[Dict[str, Any]]
        Search results returned by the vector store. When the backend is
        unavailable an empty list is returned.
    """

    pipeline = _get_vector_pipeline()
    if pipeline is None:
        return []

    try:
        if pipeline._session is None:  # type: ignore[attr-defined]
            pipeline._connect()  # type: ignore[attr-defined]
        session = pipeline._session  # type: ignore[attr-defined]
        assert session is not None
        url = f"{pipeline._db_url.rstrip('/')}/search"  # type: ignore[attr-defined]
        payload = {"vector": embedding, "top": top_k}
        response = session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("result", [])
    except Exception:  # pragma: no cover - network failures
        return []
