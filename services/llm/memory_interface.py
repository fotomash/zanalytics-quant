from __future__ import annotations

from typing import Any, List

from services.mcp2.vector.embeddings import embed


async def get_agent_context(
    query: str,
    vector_client: Any,
    top_k: int = 5,
) -> List[Any]:
    """Return agent context strings for the given query.

    Parameters
    ----------
    query:
        Natural language query whose embedding will be searched.
    vector_client:
        Client exposing an asynchronous ``query`` method.
    top_k:
        Number of nearest matches to retrieve.
    """
    query_embedding = embed(query)
    response = await vector_client.query(embedding=query_embedding, top_k=top_k)
    matches = response.get("matches", [])
    return [m.get("payload") for m in matches]
