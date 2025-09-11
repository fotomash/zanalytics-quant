from pathlib import Path

import pytest
import yaml

from core.semantic_mapping_service import SemanticMappingService


@pytest.fixture
def service(tmp_path: Path) -> SemanticMappingService:
    data = {
        "mappings": [
            {
                "primary": "agent_greeting",
                "fallback": ["agent_default"],
                "triggers": {"keywords": ["hello", "hi"]},
            },
            {
                "primary": "agent_numbers",
                "fallback": ["agent_backup"],
                "triggers": {"regex": [r"\d+"]},
            },
        ]
    }
    mapping_file = tmp_path / "mapping_interface_v2_final.yaml"
    mapping_file.write_text(yaml.safe_dump(data))
    return SemanticMappingService(mapping_file)


def test_keyword_routing(service: SemanticMappingService) -> None:
    primary, fallback = service.route("hello there")
    assert primary == "agent_greeting"
    assert fallback == ["agent_default"]


def test_regex_routing(service: SemanticMappingService) -> None:
    primary, fallback = service.route("value 123")
    assert primary == "agent_numbers"
    assert fallback == ["agent_backup"]


def test_no_match(service: SemanticMappingService) -> None:
    assert service.route("nothing to see") == (None, [])
