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

