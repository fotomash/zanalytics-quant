import runpy


def test_env_fallback(monkeypatch):
    """When HEALTH_AGGREGATOR_URL is unset the default URL is used."""
    monkeypatch.delenv("HEALTH_AGGREGATOR_URL", raising=False)
    module_globals = runpy.run_path("dashboard/components/diagnostics_panel.py")
    assert module_globals["AGGREGATOR_URL"] == module_globals["default_url"]
