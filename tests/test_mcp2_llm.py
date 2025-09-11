import pytest
import httpx
from fastapi.testclient import TestClient
from services.mcp2.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_whisperer_missing_config(client, monkeypatch):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('WHISPER_PROMPT_TEMPLATE', raising=False)
    resp = client.post('/llm/whisperer', json={'question': 'hi'})
    assert resp.status_code == 503


def test_whisperer_success(client, monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'test')
    monkeypatch.setenv('WHISPER_PROMPT_TEMPLATE', 'Echo: {question}')

    async def fake_post(self, url, headers=None, json=None, timeout=None):
        class FakeResp:
            status_code = 200

            def json(self):
                return {'choices': [{'message': {'content': 'Echo: hi'}}]}

            text = 'ok'

        return FakeResp()

    monkeypatch.setattr(httpx.AsyncClient, 'post', fake_post, raising=False)
    resp = client.post('/llm/whisperer', json={'question': 'hi'})
    assert resp.status_code == 200
    assert resp.json()['response'] == 'Echo: hi'
