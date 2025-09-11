import asyncio
import time
from datetime import datetime

import pytest
import httpx
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

import services.mcp2.routers.llm as llm_router
from backend.mcp.schemas import (
    StrategyPayloadV1,
    MarketContext,
    Features,
    RiskConfig,
    PositionsSummary,
)


@pytest.fixture
def client():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(llm_router.router)
    app.add_api_route('/health', lambda: {'status': 'ok'})
    return TestClient(app)


def _sample_payload():
    return StrategyPayloadV1(
        strategy='s',
        timestamp=datetime.utcnow(),
        market=MarketContext(symbol='BTC', timeframe='1h'),
        features=Features(indicators={}),
        risk=RiskConfig(max_risk_per_trade=1.0),
        positions=PositionsSummary(open=0, closed=0),
    ).model_dump(mode='json')


def test_openai_failure_returns_503(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'x')

    class BoomClient:
        def __init__(self, api_key):
            class Completions:
                def create(self, *a, **k):
                    raise RuntimeError('boom')

            class Chat:
                completions = Completions()

            self.chat = Chat()

    monkeypatch.setattr(llm_router, 'OpenAI', BoomClient)

    resp = client.post('/llm/whisperer', json={'payload': _sample_payload()})
    assert resp.status_code == 503


def test_slow_openai_call_does_not_block(monkeypatch):
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(llm_router.router)
    app.add_api_route('/health', lambda: {'status': 'ok'})

    monkeypatch.setenv('OPENAI_API_KEY', 'test')

    class FakeOpenAI:
        def __init__(self, api_key):
            self.chat = self
            self.completions = self

        def create(self, *a, **k):
            time.sleep(0.2)

            class Msg:
                message = type('M', (), {'content': 'Signal: x\nRisk: y\nAction: z\nJournal: j'})()

            return type('R', (), {'choices': [Msg()]})()

    monkeypatch.setattr(llm_router, 'OpenAI', FakeOpenAI)

    payload = _sample_payload()

    async def run_test():
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as slow_ac, AsyncClient(
            transport=ASGITransport(app=app), base_url='http://test'
        ) as fast_ac:
            slow_task = asyncio.create_task(
                slow_ac.post('/llm/whisperer', json={'payload': payload})
            )
            await asyncio.sleep(0.05)
            start = time.perf_counter()
            health_resp = await fast_ac.get('/health')
            elapsed = time.perf_counter() - start
            assert health_resp.status_code == 200
            assert elapsed < 0.2
            resp = await slow_task
            assert resp.status_code == 200

    asyncio.run(run_test())
