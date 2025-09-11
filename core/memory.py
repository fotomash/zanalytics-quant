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
