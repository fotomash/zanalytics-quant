import types
from unittest.mock import MagicMock, patch

import pytest

from utils import vector_backtester


def _make_result(payload):
    return types.SimpleNamespace(payload=payload)


def test_score_embedding_success():
    embedding = [0.1, 0.2]
    mock_results = [
        _make_result({"pnl": 1.0}),
        _make_result({"pnl": -1.0}),
        _make_result({"pnl": 2.0}),
    ]
    mock_client = MagicMock()
    mock_client.search.return_value = mock_results

    with patch.object(vector_backtester, "_client", mock_client):
        avg_pnl, win_rate, payloads = vector_backtester.score_embedding(embedding)

    mock_client.search.assert_called_once_with(
        collection_name=vector_backtester.QDRANT_COLLECTION,
        query_vector=embedding,
        limit=10,
    )
    assert avg_pnl == pytest.approx((1.0 - 1.0 + 2.0) / 3)
    assert win_rate == pytest.approx(2 / 3)
    assert payloads == [r.payload for r in mock_results]


def test_score_embedding_handles_errors():
    embedding = [0.5, 0.4]
    mock_client = MagicMock()
    mock_client.search.side_effect = Exception("boom")

    with patch.object(vector_backtester, "_client", mock_client):
        avg_pnl, win_rate, payloads = vector_backtester.score_embedding(embedding)

    assert avg_pnl == 0.0
    assert win_rate == 0.0
    assert payloads == []

    with patch.object(vector_backtester, "_client", None):
        avg_pnl, win_rate, payloads = vector_backtester.score_embedding(embedding)
        assert avg_pnl == 0.0
        assert win_rate == 0.0
        assert payloads == []

