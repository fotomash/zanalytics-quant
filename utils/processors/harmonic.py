"""Asynchronous storage for harmonic pattern vectors.

This module is only responsible for upserting harmonic pattern embeddings into
Qdrant.  It deliberately avoids performing any pattern *analysis* to keep the
storage concern separate from :mod:`core.harmonic_processor`.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Iterable, Sequence

from qdrant_client import models


class HarmonicStorageProcessor:
    """Persist harmonic pattern vectors into a Qdrant collection."""

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


__all__ = ["HarmonicStorageProcessor"]
