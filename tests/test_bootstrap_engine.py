from pathlib import Path

from core.bootstrap_engine import BootstrapEngine


def test_bootstrap_engine_loads_agents_and_manifest():
    engine = BootstrapEngine(base_dir=Path(__file__).resolve().parents[1])
    engine.boot()
    assert "enrichment_agent" in engine.agent_registry
    # Entry points are loaded as strings or callables
    entry_points = engine.agent_registry["enrichment_agent"].get("entry_points", {})
    assert "on_init" in entry_points and "on_message" in entry_points
    # Manifest should load if file exists
    assert engine.session_manifest is not None
