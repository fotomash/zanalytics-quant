from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import pandas as pd

MODULES_DIR = Path("services/enrichment/modules")


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, MODULES_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_structure_validator_detects_break() -> None:
    structure_validator = load_module("structure_validator")
    df = pd.DataFrame({"price": [1, 2, 8]})
    state = {"dataframe": df}
    result = structure_validator.run(state, {"threshold": 0.5})
    assert result["structure_breaks"] == [2]
    assert result["status"] == "FAIL"
