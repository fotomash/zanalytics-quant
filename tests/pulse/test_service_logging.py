import logging
import os
import sys
import types
import importlib
import pytest


def _load_service(monkeypatch):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.django.app.settings")
    os.environ.setdefault("DJANGO_SECRET_KEY", "test")

    fake_views = types.ModuleType("backend.django.app.nexus.views")
    fake_views._redis_client = lambda: None
    sys.modules["backend.django.app.nexus.views"] = fake_views

    models_mod = types.ModuleType("app.nexus.models")
    models_mod.Bar = object
    sys.modules["app.nexus.models"] = models_mod

    constants_mod = types.ModuleType("app.utils.constants")
    constants_mod.MT5Timeframe = object
    sys.modules["app.utils.constants"] = constants_mod

    api_data_mod = types.ModuleType("app.utils.api.data")
    api_data_mod.fetch_bars = lambda *args, **kwargs: None
    sys.modules["app.utils.api.data"] = api_data_mod

    gates_mod = types.ModuleType("backend.django.app.nexus.pulse.gates")
    dummy_gate = lambda *args, **kwargs: {"passed": True}
    gates_mod.context_gate = dummy_gate
    gates_mod.liquidity_gate = dummy_gate
    gates_mod.structure_gate = dummy_gate
    gates_mod.imbalance_gate = dummy_gate
    gates_mod.risk_gate = dummy_gate
    gates_mod.confluence_gate = dummy_gate
    gates_mod.wyckoff_gate = dummy_gate
    class DummyKJ:
        enabled = False
        def emit(self, *args, **kwargs):
            pass
    gates_mod.KafkaJournalEngine = DummyKJ
    sys.modules["backend.django.app.nexus.pulse.gates"] = gates_mod

    cse_mod = types.ModuleType("backend.django.app.nexus.pulse.confluence_score_engine")
    cse_mod.compute_confluence_score = lambda gates, weights, threshold=0.6: (1.0, {"score_passed": True})
    sys.modules["backend.django.app.nexus.pulse.confluence_score_engine"] = cse_mod

    service = importlib.import_module("backend.django.app.nexus.pulse.service")
    importlib.reload(service)
    return service


def test_resolve_weights_logs_on_redis_failure(monkeypatch, caplog):
    service = _load_service(monkeypatch)

    def boom():
        raise RuntimeError("boom")
    monkeypatch.setattr(service, "_redis_client", boom)

    with caplog.at_level(logging.ERROR, logger=service.logger.name):
        service._resolve_weights(None, symbol="XYZ")
    assert "resolve weights from Redis" in caplog.text


def test_resolve_threshold_logs_on_env_failure(monkeypatch, caplog):
    service = _load_service(monkeypatch)
    monkeypatch.setattr(service, "_redis_client", lambda: None)
    monkeypatch.setenv("PULSE_CONF_THRESHOLD", "bad")

    with caplog.at_level(logging.ERROR, logger=service.logger.name):
        val = service._resolve_threshold(symbol="XYZ", default=0.5)
    assert val == pytest.approx(0.5)
    assert "parse PULSE_CONF_THRESHOLD" in caplog.text


def test_pulse_status_logs_when_cache_fails(monkeypatch, caplog):
    service = _load_service(monkeypatch)

    class FailRedis:
        def get(self, key):
            return None
        def setex(self, *args, **kwargs):
            raise RuntimeError("fail")
    monkeypatch.setattr(service, "_redis_client", lambda: FailRedis())
    monkeypatch.setattr(service, "_load_minute_data", lambda symbol: {"H4": None, "H1": None, "M15": None, "M1": None})
    monkeypatch.setattr(service, "_resolve_weights", lambda weights=None, symbol=None: {"context": 1.0})
    monkeypatch.setattr(service, "_resolve_threshold", lambda symbol=None, default=0.6: 0.5)

    with caplog.at_level(logging.WARNING, logger=service.logger.name):
        status = service.pulse_status("EURUSD")
    assert status["context"] == 1
    assert "cache pulse_status to Redis" in caplog.text
