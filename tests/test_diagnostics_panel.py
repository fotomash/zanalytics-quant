import runpy
import requests


def test_get_system_health_fallback(monkeypatch):
    """When the aggregator is unreachable the mock data is returned."""

    module = runpy.run_path("dashboard/components/diagnostics_panel.py")
    get_system_health = module["get_system_health"]

    def fake_get(*args, **kwargs):
        raise requests.exceptions.RequestException()

    monkeypatch.setattr(requests, "get", fake_get)

    data = get_system_health()
    assert data["status"] == "degraded"
    assert "services" in data

