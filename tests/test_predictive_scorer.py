from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import pandas as pd
import numpy as np

MODULES_DIR = Path("services/enrichment/modules")


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, MODULES_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_predictive_scorer_outputs_score_and_grade() -> None:
    predictive_scorer = load_module("predictive_scorer")
    rows = 120
    df = pd.DataFrame({
        "open": np.linspace(1, rows, rows),
        "high": np.linspace(1, rows, rows) + 0.5,
        "low": np.linspace(1, rows, rows) - 0.5,
        "close": np.linspace(1, rows, rows),
        "volume": np.random.randint(100, 200, size=rows),
    })
    state = {"dataframe": df}
    result = predictive_scorer.run(state, {})
    assert "maturity_score" in result
    assert "grade" in result
    assert isinstance(result["maturity_score"], float)
