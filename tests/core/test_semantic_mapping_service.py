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
import yaml
from core.semantic_mapping_service import SemanticMappingService


def _create_mapping_file(tmp_path):
    data = {
        "mappings": [
            {
                "primary": "agent_alpha",
                "fallback": ["agent_beta"],
                "triggers": {
                    "keywords": ["weather"],
                    # Regex pattern that matches strings like "foo123"
                    "regex": [r"foo\d+"]
                },
            },
            {
                "primary": "agent_gamma",
                "fallback": [],
                "triggers": {"keywords": ["trade"]},
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
    with mapping_file.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh)
    return mapping_file


def test_keyword_routing(tmp_path):
    mapping_file = _create_mapping_file(tmp_path)
    service = SemanticMappingService(str(mapping_file))
    primary, fallback = service.route("Let's talk about the weather today")
    assert primary == "agent_alpha"
    assert fallback == ["agent_beta"]


def test_regex_routing(tmp_path):
    mapping_file = _create_mapping_file(tmp_path)
    service = SemanticMappingService(str(mapping_file))
    primary, fallback = service.route("foo123 is a test string")
    assert primary == "agent_alpha"
    assert fallback == ["agent_beta"]


def test_no_match(tmp_path):
    mapping_file = _create_mapping_file(tmp_path)
    service = SemanticMappingService(str(mapping_file))
    primary, fallback = service.route("no triggers here")
    assert primary is None
    assert fallback == []
