from pathlib import Path
import shutil
import yaml

from core.bootstrap_engine import BootstrapEngine


def test_bootstrap_engine_loads_agents_and_manifest(tmp_path: Path):
    base_dir = tmp_path

    # Copy existing agent definition so registry can be populated
    src_agents = Path(__file__).resolve().parents[1] / "agents"
    shutil.copytree(src_agents, base_dir / "agents")

    # Create an active session manifest inside <base_dir>/sessions
    sessions_dir = base_dir / "sessions"
    sessions_dir.mkdir()
    manifest_data = {
        "instrument_pair": "EURUSD",
        "timeframe": "M15",
        "topics": {"consume": ["raw"], "produce": "out"},
    }
    (sessions_dir / "session_manifest.yaml").write_text(yaml.safe_dump(manifest_data))

    engine = BootstrapEngine(base_dir=base_dir)
    engine.boot()

    assert "enrichment_agent" in engine.agent_registry
    entry_points = engine.agent_registry["enrichment_agent"].get("entry_points", {})
    assert "on_init" in entry_points and "on_message" in entry_points
    assert engine.session_manifest == manifest_data
    assert engine.kafka_config.consume == ["raw"]
    assert engine.kafka_config.produce == "out"
    assert engine.risk_config.instrument == "EURUSD"
    assert engine.risk_config.timeframe == "M15"
