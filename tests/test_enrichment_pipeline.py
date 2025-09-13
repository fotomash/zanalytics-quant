from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import pandas as pd
import numpy as np
from services.enrichment import pipeline

MODULES_DIR = Path("services/enrichment/modules")


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, MODULES_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fake_import_module(name: str, package: str | None = None):
    actual = name.split(".")[-1]
    return load_module(actual)


def test_pipeline_runs_all(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "import_module", fake_import_module)
    rows = 120
    df = pd.DataFrame({
        "open": np.linspace(1, rows, rows),
        "high": np.linspace(1, rows, rows) + 0.5,
        "low": np.linspace(1, rows, rows) - 0.5,
        "close": np.linspace(1, rows, rows),
        "volume": np.random.randint(100, 200, size=rows),
    })
    state = pipeline.run(df, {})
    assert state["status"] == "PASS"
    assert "liquidity_zones" in state
    assert "wyckoff_analysis" in state
    assert "maturity_score" in state
    assert "harmonic" in state
    assert hasattr(state["harmonic"], "harmonic_patterns")
    assert hasattr(state["harmonic"], "prz")
    assert hasattr(state["harmonic"], "confidence")


def test_pipeline_stops_on_failure(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "import_module", fake_import_module)
    df = pd.DataFrame({
        "open": [1, 2, 8],
        "high": [1.1, 2.1, 8.1],
        "low": [0.9, 1.9, 7.9],
        "close": [1, 2, 8],
        "volume": [100, 110, 120],
    })
    state = pipeline.run(df, {}, {"structure_validator": {"threshold": 0.5}})
    assert state["status"] == "FAIL"
    assert state["structure_breaks"]
    assert "liquidity_zones" not in state
