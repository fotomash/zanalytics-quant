from agents.registry import AGENT_REGISTRY, AgentSpec


def test_registry_contains_semantic_metadata():
    # ensure multiple agents are registered
    assert {"enrichment_agent", "analysis_agent", "risk_agent"} <= set(AGENT_REGISTRY)

    # every registry entry exposes tags and capabilities
    for spec in AGENT_REGISTRY.values():
        assert isinstance(spec, AgentSpec)
        assert spec.tags, "agent must define semantic tags"
        assert spec.capabilities, "agent must declare capabilities"

