import importlib
import sys
from types import ModuleType

from utils.enrichment_config import EnrichmentConfig


class DummyPredictiveScorer:
    def score(self, state):  # pragma: no cover - simple stub
        return {"maturity_score": 0.0}


def _import_analysis_engines():
    core_pkg = ModuleType("core")
    sys.modules.setdefault("core", core_pkg)
    cps = ModuleType("core.predictive_scorer")
    cps.PredictiveScorer = DummyPredictiveScorer
    sys.modules["core.predictive_scorer"] = cps
    sys.modules.pop("schemas", None)
    sys.modules.pop("schemas.predictive_schemas", None)
    sys.modules.pop("schemas.behavioral", None)
    ps = importlib.import_module("schemas.predictive_schemas")
    sys.modules["schemas.predictive_schemas"] = ps
    if "utils.analysis_engines" in sys.modules:
        importlib.reload(sys.modules["utils.analysis_engines"])
    return importlib.import_module("utils.analysis_engines")


def test_build_unified_analysis_includes_harmonic():
    ae = _import_analysis_engines()
    cfg = EnrichmentConfig()
    for grp in cfg.technical.groups.values():
        grp.enabled = False
    tick = {
        "symbol": "EURUSD",
        "timestamp": 0,
        "harmonic": {
            "harmonic_patterns": [{"pattern": "bat"}],
            "prz": {"low": 1.0, "high": 1.2},
            "confidence": 0.9,
        },
    }
    payload = ae.build_unified_analysis(tick, cfg)
    harmonic = payload.harmonic
    assert harmonic.harmonic_patterns[0]["pattern"] == "bat"
    assert harmonic.prz == {"low": 1.0, "high": 1.2}
    assert harmonic.confidence == 0.9
