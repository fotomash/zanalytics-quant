from agents.registry import AGENT_REGISTRY
from core.semantic_mapping_service import SemanticMappingService


def _service():
    return SemanticMappingService(AGENT_REGISTRY)


def test_resolve_returns_primary_and_fallback():
    service = _service()
    primary, fallbacks = service.resolve("please enrich this data set")
    assert primary == "enrichment_agent"
    assert fallbacks == ["analysis_agent"]


def test_resolve_handles_multiple_agents():
    service = _service()
    primary, fallbacks = service.resolve("run detailed analysis of risk")
    assert primary == "analysis_agent"
    assert fallbacks == ["risk_agent"]


def test_resolve_no_match_returns_none():
    service = _service()
    primary, fallbacks = service.resolve("say hello")
    assert primary is None
    assert fallbacks == []

