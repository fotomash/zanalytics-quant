import services.mcp2.routers.llm as llm_router
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(llm_router.router)
    return TestClient(app)


def test_run_manifest_valid_key(client, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr(llm_router, 'OpenAI', None)
    resp = client.post(
        '/llm/run_manifest',
        json={'key': 'wyckoff_simulation', 'ctx': {'ticker': 'ETH'}},
    )
    assert resp.status_code == 200
    assert 'ETH' in resp.json()['response']


def test_run_manifest_missing_key(client, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr(llm_router, 'OpenAI', None)
    resp = client.post('/llm/run_manifest', json={'key': 'missing', 'ctx': {}})
    assert resp.status_code == 404
