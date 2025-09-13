"""Tests for the :mod:`services.alert_manager.main` module."""

import logging
from types import SimpleNamespace

import requests

from services.alert_manager.main import send_alert


class DummyResponse:
    """Simple mock HTTP response object."""

    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:  # pragma: no cover - simple helper
        if self.status_code >= 400:
            raise requests.HTTPError(self.status_code)


def test_send_alert_slack_success(monkeypatch) -> None:
    """Alerts are posted to Slack when webhook URL is configured."""

    recorded = {}

    def fake_post(url, json, timeout):
        recorded["url"] = url
        recorded["json"] = json
        return DummyResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK_URL", "http://slack")

    send_alert("svc", "boom")

    assert recorded["url"] == "http://slack"
    assert "svc" in recorded["json"]["text"]


def test_send_alert_retry_and_failure_logging(monkeypatch, caplog) -> None:
    """Failures trigger retries and are logged."""

    attempts = SimpleNamespace(count=0)

    def fake_post(url, json, timeout):
        attempts.count += 1
        raise requests.RequestException("nope")

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "http://hook")

    with caplog.at_level(logging.WARNING):
        send_alert("svc", "boom")

    assert attempts.count == 3
    assert "Failed to send alert via webhook" in caplog.text
