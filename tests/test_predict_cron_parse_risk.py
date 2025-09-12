import importlib.util
from pathlib import Path
import pytest

# Dynamically load the script module since "scripts" isn't a package
spec = importlib.util.spec_from_file_location(
    "predict_cron", Path(__file__).resolve().parents[1] / "scripts" / "predict_cron.py"
)
predict_cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(predict_cron)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("85%", 0.85),
        ("risk=12%", 0.12),
    ],
)
def test_parse_risk_percent_inputs(value, expected):
    assert predict_cron._parse_risk(value) == expected


@pytest.mark.parametrize("value", ["42", 42])
def test_parse_risk_over_one(value):
    assert predict_cron._parse_risk(value) == 0.42
