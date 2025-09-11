import yaml

from core.semantic_mapping_service import SemanticMappingService


def _write_mapping_file(tmp_path):
    data = {
        "mappings": [
            {
                "triggers": {"keywords": ["balance"], "regex": ["account\\s+info"]},
                "primary": "BalanceAgent",
                "fallback": ["GeneralAgent"],
            },
            {
                "triggers": {"keywords": ["trade"]},
                "primary": "TradeAgent",
                "fallback": [],
            },
        ]
    }
    file_path = tmp_path / "mapping_interface_v2_final.yaml"
    with open(file_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh)
    return str(file_path)


def test_route_keyword_match(tmp_path):
    mapping_file = _write_mapping_file(tmp_path)
    service = SemanticMappingService(mapping_file)
    primary, fallback = service.route("What is my balance today?")
    assert primary == "BalanceAgent"
    assert fallback == ["GeneralAgent"]


def test_route_regex_match(tmp_path):
    mapping_file = _write_mapping_file(tmp_path)
    service = SemanticMappingService(mapping_file)
    primary, _ = service.route("Please give me my account info now")
    assert primary == "BalanceAgent"


def test_route_no_match(tmp_path):
    mapping_file = _write_mapping_file(tmp_path)
    service = SemanticMappingService(mapping_file)
    primary, fallback = service.route("Hello world")
    assert primary is None
    assert fallback == []
