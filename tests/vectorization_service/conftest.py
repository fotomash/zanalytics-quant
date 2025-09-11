import pytest
import yaml
from pathlib import Path


@pytest.fixture(scope="session")
def sample_payloads() -> list[dict]:
    """Load sample enriched payloads from volume_field_clarity_patch.yaml."""
    path = Path(__file__).resolve().parents[2] / "volume_field_clarity_patch.yaml"
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sample_payloads", [])


@pytest.fixture
def sample_payload(sample_payloads: list[dict]) -> dict:
    return sample_payloads[0]
