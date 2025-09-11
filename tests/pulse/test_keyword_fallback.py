import sys
import types

import pytest


def _setup_engine():
    sms_module = types.ModuleType("core.semantic_mapping_service")

    class SemanticMappingService:
        @staticmethod
        def route(agent_id: str):  # pragma: no cover - will be patched in tests
            return []

    sms_module.SemanticMappingService = SemanticMappingService
    sys.modules["core.semantic_mapping_service"] = sms_module

    from core.bootstrap_engine import BootstrapEngine  # type: ignore
    from core.semantic_mapping_service import SemanticMappingService  # type: ignore

    return BootstrapEngine, SemanticMappingService


def agent_alpha():
    return {"agent": "alpha", "confidence": 0.2}


def agent_beta():
    return {"agent": "beta", "confidence": 0.85}


def agent_gamma():
    return {"agent": "gamma", "confidence": 0.95}


def agent_delta():
    return {"agent": "delta", "confidence": 0.4}


def test_keyword_routing_triggers_fallback(monkeypatch):
    BootstrapEngine, SemanticMappingService = _setup_engine()
    mapping = {"foo": ("alpha", ["beta"]), "bar": ("gamma", ["delta"])}
    request = "foo please"
    keyword = next(k for k in mapping if k in request)
    primary, fallbacks = mapping[keyword]

    engine = BootstrapEngine(registry={})
    engine.agent_registry = {
        "alpha": {"entry_points": {"on_message": agent_alpha}},
        "beta": {"entry_points": {"on_message": agent_beta}},
    }
    monkeypatch.setattr(
        SemanticMappingService,
        "route",
        staticmethod(lambda agent_id: fallbacks if agent_id == primary else []),
    )
    result = engine.run(primary, threshold=0.8)
    assert result["agent"] == "beta"
    assert result["confidence"] == 0.85


def test_keyword_routing_skips_fallback(monkeypatch):
    BootstrapEngine, SemanticMappingService = _setup_engine()
    mapping = {"foo": ("alpha", ["beta"]), "bar": ("gamma", ["delta"])}
    request = "bar update"
    keyword = next(k for k in mapping if k in request)
    primary, fallbacks = mapping[keyword]

    engine = BootstrapEngine(registry={})
    engine.agent_registry = {
        "gamma": {"entry_points": {"on_message": agent_gamma}},
        "delta": {"entry_points": {"on_message": agent_delta}},
    }
    monkeypatch.setattr(
        SemanticMappingService,
        "route",
        staticmethod(lambda agent_id: fallbacks if agent_id == primary else []),
    )
    result = engine.run(primary, threshold=0.8)
    assert result["agent"] == "gamma"
    assert result["confidence"] == 0.95
