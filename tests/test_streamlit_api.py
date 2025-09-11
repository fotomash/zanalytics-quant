import requests
from dashboard.utils import streamlit_api


class Counter:
    def __init__(self):
        self.count = 0

    def __call__(self, path):
        self.count += 1
        return f"http://test/{path}"


def test_safe_api_call_success(monkeypatch):
    counter = Counter()

    def fake_request(method, url, payload, timeout):
        class Response:
            status_code = 200

            def json(self):
                return {"ok": True}

        assert url == "http://test/endpoint"
        return Response()

    monkeypatch.setattr(streamlit_api, "api_url", counter)
    monkeypatch.setattr(streamlit_api, "_session_request", fake_request)
    result = streamlit_api.safe_api_call("GET", "endpoint")
    assert result == {"ok": True}
    assert counter.count == 1


def test_safe_api_call_timeout(monkeypatch):
    counter = Counter()

    def fake_request(method, url, payload, timeout):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(streamlit_api, "api_url", counter)
    monkeypatch.setattr(streamlit_api, "_session_request", fake_request)
    result = streamlit_api.safe_api_call("POST", "endpoint", payload={})
    assert result == {"error": "API timeout", "url": "http://test/endpoint"}
    assert counter.count == 1


def test_safe_api_call_connection_error(monkeypatch):
    counter = Counter()

    def fake_request(method, url, payload, timeout):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(streamlit_api, "api_url", counter)
    monkeypatch.setattr(streamlit_api, "_session_request", fake_request)
    result = streamlit_api.safe_api_call("GET", "endpoint")
    assert result == {"error": "API connection failed", "url": "http://test/endpoint"}
    assert counter.count == 1
