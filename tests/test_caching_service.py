import json
import fakeredis
from llm_redis_bridge import LLMRedisBridge


def test_llm_redis_bridge_writes_context_with_ttl():
    r = fakeredis.FakeRedis(decode_responses=True)
    r.flushall()
    bridge = LLMRedisBridge(redis_client=r)
    payload = {
        "market_data": {"BTC": {"price": 42000}},
        "analysis_results": {"signal": "buy"},
    }

    bridge.store_llm_context("agent-1", payload)

    key = "llm_agent:context:agent-1"
    raw = r.get(key)
    assert raw is not None
    data = json.loads(raw)
    assert data["agent_id"] == "agent-1"
    assert "timestamp" in data
    assert r.ttl(key) <= 1800 and r.ttl(key) > 0
    r.flushall()
