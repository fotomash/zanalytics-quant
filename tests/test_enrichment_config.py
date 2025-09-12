import importlib
import sys
from types import ModuleType

from utils.enrichment_config import EnrichmentConfig


class DummyPredictiveScorer:
    def score(self, state):
        return {"maturity_score": 0.0}


def _import_analysis_engines():
    """Import ``utils.analysis_engines`` with core scorer stubbed."""
    core_pkg = ModuleType("core")
    sys.modules.setdefault("core", core_pkg)
    cps = ModuleType("core.predictive_scorer")
    cps.PredictiveScorer = DummyPredictiveScorer
    sys.modules["core.predictive_scorer"] = cps
    return importlib.import_module("utils.analysis_engines")


def test_default_groups_present():
    cfg = EnrichmentConfig()
    assert "momentum" in cfg.technical.groups
    assert "volatility" in cfg.technical.groups


def test_build_unified_analysis_skips_technical(monkeypatch):
    ae = _import_analysis_engines()
    cfg = EnrichmentConfig()
    for grp in cfg.technical.groups.values():
        grp.enabled = False

    called = False

    def fake_confluence(tick):
        nonlocal called
        called = True
        return {"score": 1}

    monkeypatch.setattr(
        ae.confluence_engine, "compute_confluence_indicators_df", fake_confluence
    )
    tick = {"symbol": "EURUSD", "timestamp": 0}
    payload = ae.build_unified_analysis(tick, cfg)
    assert not called
    assert payload.technical_indicators.extras == {}

