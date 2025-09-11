"""Tests for diagnostics helpers."""

from __future__ import annotations

import requests

from metrics import prometheus
from utils import health


def test_fetch_service_health(monkeypatch):
    """Services responding with 200 are marked healthy."""

    def fake_get(url, timeout):
        class Resp:
            status_code = 200

        if "good" in url:
            return Resp()
        raise requests.RequestException

    monkeypatch.setattr(health.requests, "get", fake_get)
    services = {"good": "http://good", "bad": "http://bad"}
    result = health.fetch_service_health(services=services)
    assert result == {"good": True, "bad": False}


def test_fetch_metrics(monkeypatch):
    """Prometheus metrics are parsed into floats."""

    def fake_get(url, params, timeout):
        class Resp:
            def json(self):
                return {"data": {"result": [{"value": [0, "123"]}]}}

            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setattr(prometheus, "_load_prometheus_url", lambda config_path=None: "http://prom")
    monkeypatch.setattr(prometheus.requests, "get", fake_get)

    queries = {"Messages Processed": "messages_processed_total"}
    result = prometheus.fetch_metrics(queries=queries)
    assert result["Messages Processed"] == 123.0
