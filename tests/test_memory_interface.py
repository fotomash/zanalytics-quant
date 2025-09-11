import asyncio
from unittest.mock import AsyncMock, patch

from services.llm.memory_interface import get_agent_context


def test_get_agent_context_uses_embeddings_and_vector_store():
    async def run():
        store = AsyncMock()
        store.query.return_value = {
            "matches": [
                {"payload": "one"},
                {"payload": "two"},
            ]
        }
        with patch(
            "services.llm.memory_interface.embed", return_value=[0.1, 0.2, 0.3]
        ) as mock_embed:
            result = await get_agent_context("my query", store, top_k=2)
            mock_embed.assert_called_once_with("my query")
            store.query.assert_awaited_once_with(embedding=[0.1, 0.2, 0.3], top_k=2)
            assert result == ["one", "two"]

    asyncio.run(run())
