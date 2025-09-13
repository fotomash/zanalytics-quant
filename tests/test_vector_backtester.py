from types import SimpleNamespace

import pytest

from utils import vector_backtester
from utils.vector_backtester import score_embedding


def test_score_embedding_returns_metrics(monkeypatch):
    instances = {}

    class DummyClient:
        def __init__(self, url=None, api_key=None):
            instances['url'] = url
            instances['api_key'] = api_key

        def search(self, **kwargs):
            instances['search_kwargs'] = kwargs
            return [
                SimpleNamespace(payload={'pnl': 1.0, 'outcome': True}),
                SimpleNamespace(payload={'pnl': -0.5, 'outcome': False}),
            ]

    monkeypatch.setenv('QDRANT_URL', 'http://localhost')
    monkeypatch.setenv('QDRANT_API_KEY', 'token')
    monkeypatch.setenv('QDRANT_COLLECTION', 'testcol')
    monkeypatch.setattr(vector_backtester, 'QdrantClient', DummyClient)

    avg_pnl, win_rate, payloads = score_embedding([0.1, 0.2])

    assert instances['url'] == 'http://localhost'
    assert instances['api_key'] == 'token'
    assert instances['search_kwargs']['collection_name'] == 'testcol'
    assert instances['search_kwargs']['query_vector'] == [0.1, 0.2]
    assert avg_pnl == pytest.approx(0.25)
    assert win_rate == pytest.approx(0.5)
    assert payloads == [
        {'pnl': 1.0, 'outcome': True},
        {'pnl': -0.5, 'outcome': False},
    ]


def test_score_embedding_handles_errors(monkeypatch):
    class FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):  # pragma: no cover - behavior validation
            raise RuntimeError('boom')

    monkeypatch.setattr(vector_backtester, 'QdrantClient', FailingClient)

    avg_pnl, win_rate, payloads = score_embedding([1.0])

    assert (avg_pnl, win_rate, payloads) == (0.0, 0.0, [])
=======


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
        
