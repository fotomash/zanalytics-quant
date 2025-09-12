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


def test_context_analyzer_merges_results() -> None:
    context_analyzer = load_module("context_analyzer")
    df = pd.DataFrame({
        "open": range(20),
        "high": [x + 0.5 for x in range(20)],
        "low": [x - 0.5 for x in range(20)],
        "close": range(20),
        "volume": [100] * 20,
    })
    state = {"dataframe": df, "status": "PASS"}
    result = context_analyzer.run(state, {})
    assert "wyckoff_analysis" in result
    assert "wyckoff_current_phase" in result
    assert result["status"] == result["wyckoff_current_phase"]
