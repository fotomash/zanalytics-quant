from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import numpy as np
import pandas as pd

MODULES_DIR = Path("services/enrichment/modules")
CORE_DIR = Path("core")

# Bypass core package __init__ to avoid heavy dependencies during tests
core_pkg = types.ModuleType("core")
core_pkg.__path__ = [str(CORE_DIR)]
sys.modules.setdefault("core", core_pkg)


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, MODULES_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_core(name: str):
    module_name = f"core.{name}"
    spec = importlib.util.spec_from_file_location(module_name, CORE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_liquidity_engine_parity():
    module = load_module("liquidity_engine")
    LiquidityEngine = load_core("liquidity_engine").LiquidityEngine

    df = pd.DataFrame({
        "open": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "high": [1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1],
        "low": [0.9, 1.9, 2.9, 3.9, 4.9, 5.9, 6.9, 7.9, 8.9, 9.9],
        "close": [1.05, 2.05, 3.05, 4.05, 5.05, 6.05, 7.05, 8.05, 9.05, 10.05],
    })
    state = {"dataframe": df}
    result = module.run(state.copy(), {})
    expected = LiquidityEngine().analyze(df)

    assert result["status"] == "PASS"
    assert result["liquidity_zones"] == expected["liquidity_zones"]
    assert result["order_blocks"] == expected["order_blocks"]
    assert result["fair_value_gaps"] == expected["fair_value_gaps"]


def test_context_analyzer_parity():
    module = load_module("context_analyzer")
    ContextAnalyzer = load_core("context_analyzer").ContextAnalyzer

    rows = 120
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "open": np.linspace(1, rows, rows),
        "high": np.linspace(1, rows, rows) + 0.5,
        "low": np.linspace(1, rows, rows) - 0.5,
        "close": np.linspace(1, rows, rows),
        "volume": rng.integers(100, 200, size=rows),
    })
    state = {"dataframe": df}
    result = module.run(state.copy(), {})
    expected = ContextAnalyzer().analyze(df)

    assert result["wyckoff_analysis"]["phase"] == expected["phase"]
    assert result["wyckoff_analysis"]["sos_sow"] == expected["sos_sow"]


def test_predictive_scorer_parity():
    module = load_module("predictive_scorer")
    PredictiveScorer = load_core("predictive_scorer").PredictiveScorer

    df = pd.DataFrame({
        "open": [1, 2, 3],
        "high": [1.1, 2.1, 3.1],
        "low": [0.9, 1.9, 2.9],
        "close": [1.05, 2.05, 3.05],
        "volume": [100, 110, 120],
    })
    state = {"dataframe": df}
    result = module.run(state.copy(), {})
    expected = PredictiveScorer({}).score(state.copy())

    assert result["maturity_score"] == expected["maturity_score"]
    assert result["grade"] == expected["grade"]
