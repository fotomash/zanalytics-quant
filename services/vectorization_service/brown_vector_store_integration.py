"""Integration pipeline for external vector stores.

This module provides :class:`BrownVectorPipeline`, a lightweight wrapper
around a remote vector database. Qdrant is the currently supported store, and
connection parameters are supplied via the ``QDRANT_URL`` and
``QDRANT_API_KEY`` environment variables. Support for an in-memory Faiss
backend is planned, while previous integrations with Pinecone or Chroma are
considered deprecated and may return in the future.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


class BrownVectorPipeline:
    """Simple integration layer for vector databases.

    The pipeline maintains a persistent HTTP session and will automatically
    reconnect if a request fails. It expects the following environment
    variables to be defined:

    ``QDRANT_URL``
        Base URL for the vector database service.
    ``QDRANT_API_KEY``
        API key used for authentication.
    """

    def __init__(self) -> None:
        self._db_url = os.getenv("QDRANT_URL")
        self._api_key = os.getenv("QDRANT_API_KEY")
        if not self._db_url or not self._api_key:
            raise EnvironmentError(
                "QDRANT_URL and QDRANT_API_KEY must be set to use BrownVectorPipeline"
            )
        self._session: requests.Session | None = None
        self._connect()

    def _connect(self) -> None:
        """Establish an HTTP session with the vector database."""
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {self._api_key}"})
        self._session = session

    def upsert_vector(self, id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        """Upsert a vector into the configured vector database.

        Parameters
        ----------
        id:
            Unique identifier for the vector entry.
        embedding:
            List of floating point numbers representing the vector.
        metadata:
            Additional metadata to associate with the vector.
        """
        payload = {"id": id, "embedding": embedding, "metadata": metadata}
        try:
            self._post(payload)
        except Exception as exc:  # pragma: no cover - network failures are environment specific
            logger.warning("Vector DB upsert failed, attempting reconnect: %s", exc)
            self._connect()
            self._post(payload)

    def _post(self, payload: Dict[str, Any]) -> None:
        if self._session is None:  # Safety check; should not happen
            self._connect()
        assert self._session is not None
        url = f"{self._db_url.rstrip('/')}/upsert"
        response = self._session.post(url, json=payload, timeout=30)
        response.raise_for_status()

    def search_similar_clusters(
        self, collection_name: str, query_vector: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search the vector database for entries similar to ``query_vector``.

        Parameters
        ----------
        collection_name:
            Name of the collection to search.
        query_vector:
            Vector to compare against stored entries.
        top_k:
            Maximum number of matches to return.

        Returns
        -------
        List[Dict[str, Any]]
            Search results from the vector database.  On failure an empty list
            is returned.
        """

        if self._session is None:
            self._connect()
        assert self._session is not None
        url = f"{self._db_url.rstrip('/')}/{collection_name}/search"
        payload = {"vector": query_vector, "top": top_k}
        try:
            response = self._session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("result", [])
        except Exception as exc:  # pragma: no cover - network failures are environment specific
            logger.warning("Vector DB search failed: %s", exc)
            return []


__all__ = ["BrownVectorPipeline"]
