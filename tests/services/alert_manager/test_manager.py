"""Tests for the :mod:`services.alert_manager.manager` module."""

from datetime import datetime

from services.alert_manager.manager import Alert, AlertManager


def test_create_price_alert_defaults() -> None:
    """``create_price_alert`` builds a complete :class:`Alert`."""
    manager = AlertManager()
    alert = manager.create_price_alert("BTC", 110.0, 100.0, "above")

    assert isinstance(alert, Alert)
    assert alert.type == "price"
    assert alert.severity == "high"
    assert alert.title == "Price Alert: BTC"
    assert alert.channels == ["discord"]
    assert alert.data["symbol"] == "BTC"
    assert isinstance(alert.timestamp, datetime)


def test_send_alert_dispatch() -> None:
    """``send_alert`` routes alerts to registered channels."""
    manager = AlertManager()
    received: list[Alert] = []

    def handler(alert: Alert) -> None:
        received.append(alert)

    manager.register_channel("discord", handler)
    alert = manager.create_price_alert(
        "BTC", 110.0, 100.0, "above", channels=["discord", "email"]
    )

    results = manager.send_alert(alert)

    assert received == [alert]
    assert results["discord"]["success"] is True
    assert results["email"]["success"] is False
    assert "error" in results["email"]

