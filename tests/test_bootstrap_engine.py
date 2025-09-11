from pathlib import Path
import shutil
import yaml
import sys
import types

from agents.registry import AGENT_REGISTRY


class _StubSemanticMappingService:
    def __init__(self, *args, **kwargs):
        pass


sys.modules.setdefault(
    "core.semantic_mapping_service",
    types.SimpleNamespace(SemanticMappingService=_StubSemanticMappingService),
)

from core.bootstrap_engine import BootstrapEngine

REGISTRY_PATHS = {k: v.path for k, v in AGENT_REGISTRY.items()}


def test_bootstrap_engine_loads_agents_and_manifest(tmp_path: Path):
    base_dir = tmp_path

    # Copy existing agent definition so registry can be populated
    src_agents = Path(__file__).resolve().parents[1] / "agents"
    shutil.copytree(src_agents, base_dir / "agents")

    # Create an active session manifest inside <base_dir>/sessions
    sessions_dir = base_dir / "sessions"
    sessions_dir.mkdir()
    manifest_data = {
        "prompt_version": "v1",
        "instrument_pair": "EURUSD",
        "ingestion_service": {"source": "test"},
        "enrichment_service": {"level": "basic"},
        "timeframe": "M15",
        "topics": {"consume": ["raw"], "produce": "out"},
    }
    (sessions_dir / "session_manifest.yaml").write_text(yaml.safe_dump(manifest_data))

    engine = BootstrapEngine(base_dir=base_dir, registry=REGISTRY_PATHS)

    calls = {}

    def fake_ingestion(self, config):
        calls["ingestion"] = config

    def fake_enrichment(self, config):
        calls["enrichment"] = config

    engine.start_ingestion_service = fake_ingestion.__get__(engine, BootstrapEngine)
    engine.start_enrichment_service = fake_enrichment.__get__(engine, BootstrapEngine)

    engine.boot()

    assert calls["ingestion"] == manifest_data["ingestion_service"]
    assert calls["enrichment"] == manifest_data["enrichment_service"]
    assert "enrichment_agent" in engine.agent_registry
    entry_points = engine.agent_registry["enrichment_agent"].get("entry_points", {})
    assert "on_init" in entry_points and "on_message" in entry_points
    assert engine.session_manifest == manifest_data
    assert engine.kafka_config.consume == ["raw"]
    assert engine.kafka_config.produce == "out"
    assert engine.risk_config.instrument == "EURUSD"
    assert engine.risk_config.timeframe == "M15"


def test_execution_validation_config(tmp_path: Path):
    base_dir = tmp_path

    src_agents = Path(__file__).resolve().parents[1] / "agents"
    shutil.copytree(src_agents, base_dir / "agents")

    sessions_dir = base_dir / "sessions"
    sessions_dir.mkdir()
    manifest_data = {
        "prompt_version": "v1",
        "instrument_pair": "EURUSD",
        "timeframe": "M15",
        "topics": {"consume": ["raw"], "produce": "out"},
    }
    (sessions_dir / "session_manifest.yaml").write_text(yaml.safe_dump(manifest_data))

    cfg_dir = base_dir / "config"
    cfg_dir.mkdir()
    cfg = {"confidence_threshold": 0.75, "fallback_limits": {"max_retries": 2}}
    (cfg_dir / "execution_validation.yaml").write_text(yaml.safe_dump(cfg))

    engine = BootstrapEngine(base_dir=base_dir, registry=REGISTRY_PATHS)
    engine.boot()

    assert engine.execution_confidence_threshold == 0.75
    assert engine.execution_validation_config is not None
    assert engine.execution_validation_config.fallback_limits == {"max_retries": 2}


def test_sessions_manifest_precedence(tmp_path: Path):
    base_dir = tmp_path

    base_manifest = {
        "prompt_version": "v1",
        "instrument_pair": "BASE",
        "timeframe": "M1",
        "topics": {"consume": ["base"], "produce": "base_out"},
    }
    (base_dir / "session_manifest.yaml").write_text(yaml.safe_dump(base_manifest))

    sessions_dir = base_dir / "sessions"
    sessions_dir.mkdir()
    session_manifest = {
        "prompt_version": "v1",
        "instrument_pair": "SESSION",
        "timeframe": "M5",
        "topics": {"consume": ["session"], "produce": "session_out"},
    }
    (sessions_dir / "session_manifest.yaml").write_text(yaml.safe_dump(session_manifest))

    engine = BootstrapEngine(base_dir=base_dir, registry=REGISTRY_PATHS)
    manifest = engine._load_session_manifest()

    assert manifest == session_manifest
