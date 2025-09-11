from pathlib import Path

from core.session_manager import build_session_manifest


def test_build_session_manifest_applies_defaults_and_metadata():
    design_path = Path(__file__).resolve().parents[1] / "session_manager_design.yaml"
    responses = {"instrument_pair": "GBPUSD"}
    manifest = build_session_manifest(responses, design_path)

    assert manifest["instrument_pair"] == "GBPUSD"
    assert manifest["timeframe"] == "M15"
    assert manifest["topics"]["consume"] == ["raw-market-data"]
    assert manifest["prompt_version"] == "v1"
    assert "created_at" in manifest["metadata"]
