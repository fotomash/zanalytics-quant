"""Tests for the :class:`~core.semantic_mapping_service.SemanticMappingService`."""

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
