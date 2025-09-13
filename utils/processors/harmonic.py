
"""Harmonic pattern utilities with asynchronous Qdrant insertion.

This module exposes :class:`HarmonicProcessor` which mirrors the style of
other processors under :mod:`utils.processors`. The processor accepts either
an :class:`qdrant_client.AsyncQdrantClient` or the traditional synchronous
:class:`qdrant_client.QdrantClient`. Inserts are executed in a non-blocking
fashion: asynchronous clients are awaited directly while synchronous clients
are dispatched to a background thread using :func:`asyncio.to_thread`.

The goal is to provide a simple, awaitable interface for storing detected
harmonic patterns without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Iterable, Sequence

from qdrant_client import models


class HarmonicProcessor:
    """Processor responsible for persisting harmonic pattern vectors."""

    def __init__(self, client: object, collection_name: str = "harmonic") -> None:
        """Initialize the processor with a Qdrant client.

        Parameters
        ----------
        client:
            Instance of :class:`~qdrant_client.QdrantClient` or
            :class:`~qdrant_client.AsyncQdrantClient`.
        collection_name:
            Qdrant collection used for storage.
        """

        self._client = client
        self._collection = collection_name
        self._is_async = inspect.iscoroutinefunction(getattr(client, "upsert", None))

    async def upsert(
        self,
        vectors: Sequence[Sequence[float]],
        payloads: Iterable[dict],
        ids: Iterable[int],
    ) -> None:
        """Insert vectors into Qdrant asynchronously.

        The method adapts to either an asynchronous or synchronous Qdrant
        client. Synchronous clients are executed in a background thread via
        :func:`asyncio.to_thread`, mirroring patterns used in other asynchronous
        utilities.
        """

        points = [
            models.PointStruct(id=pid, vector=vec, payload=payload)
            for pid, vec, payload in zip(ids, vectors, payloads)
        ]
        if self._is_async:
            await self._client.upsert(collection_name=self._collection, points=points)
        else:
            await asyncio.to_thread(
                self._client.upsert,
                collection_name=self._collection,
                points=points,
            )


__all__ = ["HarmonicProcessor"]

