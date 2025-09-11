from core.bootstrap_engine import BootstrapEngine
from core.semantic_mapping_service import SemanticMappingService


def test_run_routes_tasks_and_uses_fallback():
    calls = []

    def primary(task):
        calls.append(("primary", task))
        raise RuntimeError("boom")

    def fallback(task):
        calls.append(("fallback", task))

    service = SemanticMappingService({"work": ("agent_a", ["agent_b"])})
    engine = BootstrapEngine(semantic_service=service)
    engine.agent_registry = {
        "agent_a": {"entry_points": {"on_message": primary}},
        "agent_b": {"entry_points": {"on_message": fallback}},
    }

    engine.run([{"name": "work"}])

    assert calls == [
        ("primary", {"name": "work"}),
        ("fallback", {"name": "work"}),
    ]
