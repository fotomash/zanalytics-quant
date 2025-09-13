import importlib
import sys
from types import ModuleType

import yaml
import pytest

from utils.enrichment_config import EnrichmentConfig, load_enrichment_config


class DummyPredictiveScorer:
    def score(self, state):
        return {"maturity_score": 0.0}


def _import_analysis_engines():
    """Import ``utils.analysis_engines`` with core scorer stubbed."""
    core_pkg = ModuleType("core")
    sys.modules["core"] = core_pkg
    cps = ModuleType("core.predictive_scorer")
    cps.PredictiveScorer = DummyPredictiveScorer
    sys.modules["core.predictive_scorer"] = cps
    sys.modules.pop("utils.analysis_engines", None)
    return importlib.import_module("utils.analysis_engines")


def test_default_groups_present():
    cfg = EnrichmentConfig()
    assert "momentum" in cfg.technical.groups
    assert "volatility" in cfg.technical.groups


def test_rsi_threshold_defaults():
    cfg = EnrichmentConfig()
    assert cfg.technical.overbought_threshold == 70
    assert cfg.technical.oversold_threshold == 30


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


def _write_cfg(tmp_path, data):
    file = tmp_path / "cfg.yaml"
    file.write_text(yaml.safe_dump(data))
    return file


def test_missing_vector_db_collection(tmp_path):
    path = _write_cfg(
        tmp_path,
        {
            "advanced": {"harmonic": {"enabled": True, "collection": "harmonic_patterns"}},
            "embedding": {"model": "text-embedding-3-small"},
        },
    )
    with pytest.raises(ValueError, match="vector_db.collection"):
        load_enrichment_config(path)


def test_missing_harmonic_options(tmp_path):
    path = _write_cfg(
        tmp_path,
        {
            "vector_db": {"collection": "foo"},
            "embedding": {"model": "text-embedding-3-small"},
        },
    )
    with pytest.raises(ValueError, match="advanced.harmonic"):
        load_enrichment_config(path)


def test_missing_embedding_model(tmp_path):
    path = _write_cfg(
        tmp_path,
        {
            "vector_db": {"collection": "foo"},
            "advanced": {"harmonic": {"enabled": True, "collection": "harmonic_patterns"}},
        },
    )
    with pytest.raises(ValueError, match="embedding.model"):
        load_enrichment_config(path)


def test_load_enrichment_config_missing_file(tmp_path):
    non_existent_path = tmp_path / "non_existent_config.yaml"
    cfg = load_enrichment_config(non_existent_path)
    assert isinstance(cfg, EnrichmentConfig)
    # Assert some default values to ensure it's a default config
    assert cfg.core.structure_validator is True
    assert cfg.advanced.elliott.enabled is True


def test_build_unified_analysis_passes_smc_toggles(monkeypatch):
    ae = _import_analysis_engines()
    cfg = EnrichmentConfig()
    for grp in cfg.technical.groups.values():
        grp.enabled = False
    cfg.structure.smc_features = {"liquidity_sweeps": False}

    captured: dict = {}

    class DummySMCAnalyzer:
        def __init__(self, *_, features=None, **__):
            captured["features"] = features

        def analyze(self, df):  # pragma: no cover - simple stub
            return {}

    smc_mod = ModuleType("core.smc_analyzer")
    smc_mod.SMCAnalyzer = DummySMCAnalyzer
    sys.modules["core.smc_analyzer"] = smc_mod

    tick = {
        "symbol": "EURUSD",
        "timestamp": 0,
        "bars": [{"open": 1, "high": 1, "low": 1, "close": 1}],
    }
    ae.build_unified_analysis(tick, cfg)

    assert captured["features"] == {"liquidity_sweeps": False}
