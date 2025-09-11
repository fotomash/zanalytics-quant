from __future__ import annotations

from typing import Any, List, Sequence

from services.mcp2.vector.embeddings import embed
from services.mcp2.vector import FaissStore


async def get_agent_context(
    query: str,
    store: FaissStore,
    top_k: int = 5,
) -> List[Any]:
    """Return agent context strings for the given query.

    Parameters
    ----------
    query:
        Natural language query whose embedding will be searched.
    store:
        :class:`FaissStore` instance used for similarity search. The store can
        be configured with a maximum size and optional time-to-live (TTL)
        threshold. When the index exceeds its capacity, stale vectors are
        pruned using TTL and least-recently-used (LRU) strategies.
    top_k:
        Number of nearest matches to retrieve.
    """
    query_embedding = embed(query)
    response = await store.query(embedding=query_embedding, top_k=top_k)
    # Ensure the embedding is a simple list of floats for downstream clients.
    query_embedding: Sequence[float] = list(embed(query))
    response = await vector_client.query(embedding=query_embedding, top_k=top_k)
    matches = response.get("matches", [])
    return [m.get("payload") for m in matches]
