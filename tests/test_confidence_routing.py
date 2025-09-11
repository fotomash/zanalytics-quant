from core.bootstrap_engine import BootstrapEngine
from core.semantic_mapping_service import SemanticMappingService


def primary_agent():
    return {"value": "primary", "confidence": 0.2}


def fallback_one():
    return {"value": "fb1", "confidence": 0.4}


def fallback_two():
    return {"value": "fb2", "confidence": 0.9}


def test_run_uses_fallbacks_when_threshold_not_met(monkeypatch):
    engine = BootstrapEngine(registry={})
    engine.agent_registry = {
        "primary": {"entry_points": {"on_message": primary_agent}},
        "fb1": {"entry_points": {"on_message": fallback_one}},
        "fb2": {"entry_points": {"on_message": fallback_two}},
    }

    monkeypatch.setattr(
        SemanticMappingService,
        "route",
        staticmethod(lambda agent_id: ["fb1", "fb2"]),
    )

    result = engine.run("primary", threshold=0.8)
    assert result["value"] == "fb2"


def test_run_returns_highest_even_if_threshold_unreached(monkeypatch):
    engine = BootstrapEngine(registry={})
    engine.agent_registry = {
        "primary": {"entry_points": {"on_message": primary_agent}},
        "fb1": {"entry_points": {"on_message": fallback_one}},
        "fb2": {"entry_points": {"on_message": fallback_two}},
    }
    monkeypatch.setattr(
        SemanticMappingService,
        "route",
        staticmethod(lambda agent_id: ["fb1", "fb2"]),
    )

    result = engine.run("primary", threshold=0.95)
    assert result["value"] == "fb2"
