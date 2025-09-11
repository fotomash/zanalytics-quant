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


def test_liquidity_engine_populates_state() -> None:
    liquidity_engine = load_module("liquidity_engine")
    df = pd.DataFrame({
        "open": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "high": [1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1],
        "low": [0.9, 1.9, 2.9, 3.9, 4.9, 5.9, 6.9, 7.9, 8.9, 9.9],
        "close": [1.05, 2.05, 3.05, 4.05, 5.05, 6.05, 7.05, 8.05, 9.05, 10.05],
    })
    state = {"dataframe": df}
    result = liquidity_engine.run(state, {})
    assert result["status"] == "PASS"
    for key in [
        "liquidity_zones",
        "order_blocks",
        "fair_value_gaps",
        "market_structure",
        "liquidity_sweeps",
        "displacement",
        "inducement",
    ]:
        assert key in result
