import logging
from unittest.mock import patch

from utils import session_cache


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_with_cache_logs_on_redis_errors(caplog):
    payload = {"ok": True}
    with patch.object(session_cache.r, "get", side_effect=Exception("get boom")):
        with patch.object(session_cache.r, "setex", side_effect=Exception("set boom")):
            with patch("utils.session_cache.requests.post", return_value=DummyResp(payload)):
                with caplog.at_level(logging.WARNING):
                    result = session_cache._fetch_with_cache("http://api", None, "session_boot", {}, "u1")
    assert result == payload
    messages = [rec.getMessage() for rec in caplog.records]
    assert any("session_boot:u1" in m for m in messages)
    assert any("Error retrieving cache key" in m for m in messages)
    assert any("Error setting cache key" in m for m in messages)
