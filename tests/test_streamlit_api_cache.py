import json
from unittest.mock import MagicMock
import fakeredis

import dashboard.utils.streamlit_api as api


def _setup_fake_redis(monkeypatch):
    r = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(api, "_cache_redis", r)
    monkeypatch.setattr(api, "api_url", lambda path: "http://example.com")
    return r


def test_safe_api_call_redis_hit_avoids_http(monkeypatch):
    r = _setup_fake_redis(monkeypatch)
    key = "streamlit_api:GET:http://example.com:"
    r.set(key, json.dumps({"foo": "bar"}))
    http_get = MagicMock()
    monkeypatch.setattr(api.requests, "get", http_get)
    result = api.safe_api_call("GET", "/sample")
    assert result == {"foo": "bar"}
    http_get.assert_not_called()


def test_safe_api_call_cache_miss_triggers_http(monkeypatch):
    r = _setup_fake_redis(monkeypatch)
    response = MagicMock(status_code=200, json=lambda: {"baz": 1})
    http_get = MagicMock(return_value=response)
    monkeypatch.setattr(api.requests, "get", http_get)
    result = api.safe_api_call("GET", "/sample", ttl=5)
    assert result == {"baz": 1}
    http_get.assert_called_once()
    key = "streamlit_api:GET:http://example.com:"
    assert json.loads(r.get(key)) == {"baz": 1}
    ttl = r.ttl(key)
    assert 0 < ttl <= 5
