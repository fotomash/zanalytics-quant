"""Vector-based memory module for similarity search."""

from __future__ import annotations

from typing import Any, List


class Memory:
    """Simple wrapper around a vector store client.

    The memory is backed by an external vector store client that provides
    similarity search capabilities.  This class stores a reference to the
    client so that higher level components can perform searches without
    needing to know the underlying implementation details of the vector
    database.
    """

    def __init__(self, vector_client: Any) -> None:
        """Initialise the memory with a vector store client.

        Parameters
        ----------
        vector_client:
            Client instance implementing a ``similarity_search`` method.  The
            client will be used for all subsequent similarity queries.
        """

        self._vector_client = vector_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def similarity_search(self, query: Any, k: int = 5, **kwargs: Any) -> List[Any]:
        """Return the top ``k`` items similar to ``query``.

        This method simply proxies to the underlying vector store client's
        ``similarity_search`` implementation.
        """

        if self._vector_client is None:
            raise ValueError("No vector client provided")

        return self._vector_client.similarity_search(query, k=k, **kwargs)

from __future__ import annotations

from typing import Any, Dict, List, Protocol

from utils.llm_connector import embed_query


class VectorClient(Protocol):
    def similarity_search(self, embedding: List[float], agent_id: str, k: int) -> List[Any]:
        ...


class AgentMemoryInterface:
    """Interface for retrieving agent context from a vector store."""

    def __init__(self, vector_client: VectorClient) -> None:
        self.vector_client = vector_client

    def get_agent_context(self, agent_id: str, query: str, k: int = 5) -> List[Dict]:
        """Retrieve top-``k`` memory payloads relevant to the query.

        The query is embedded using the project's embedding utility and a
        similarity search is executed against the provided vector store.

        Parameters
        ----------
        agent_id:
            Identifier for the agent's namespace in the vector store.
        query:
            Natural language query to embed and search.
        k:
            Number of results to return. Defaults to 5.

        Returns
        -------
        List[Dict]
            Payload dictionaries from the top matches, ordered by relevance.
            Each dictionary mirrors the ``payload`` field stored in the vector
            database (e.g., ``{"text": "hello", "created": "2024-01-01"}``).
        """
        embedding = embed_query(query)
        results = self.vector_client.similarity_search(embedding, agent_id, k)
        payloads: List[Dict] = []
        for item in results[:k]:
            if isinstance(item, dict):
                payloads.append(item.get("payload", item))
            else:
                payloads.append(getattr(item, "payload", item))
        return payloads

"""Abstractions for agent memory storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AgentMemoryInterface(ABC):
    """Interface for memory backends used by agents.

    Implementations are responsible for persisting and retrieving
    memory items for a given agent identifier.
    """

    @abstractmethod
    def save(self, agent_id: str, memory: Dict[str, Any]) -> None:
        """Persist a single memory item for an agent."""

    @abstractmethod
    def load(self, agent_id: str) -> List[Dict[str, Any]]:
        """Return an ordered collection of memory items for ``agent_id``."""

    @abstractmethod
    def clear(self, agent_id: str) -> None:
        """Remove all stored memory for ``agent_id``."""


__all__ = ["AgentMemoryInterface"]
