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
