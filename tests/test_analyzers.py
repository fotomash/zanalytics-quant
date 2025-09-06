import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from agents.analyzers import detect_wyckoff_patterns, detect_smc, compute_confluence


def wyckoff_df():
    return pd.DataFrame([
        {"open": 1, "high": 1, "low": 0.5, "close": 0.8},
        {"open": 0.8, "high": 5, "low": 0.5, "close": 4},
        {"open": 4, "high": 10, "low": 3, "close": 8},
        {"open": 8, "high": 5, "low": 3, "close": 4},
        {"open": 4, "high": 1, "low": 0.5, "close": 0.8},
    ])


def smc_df():
    return pd.DataFrame([
        {"open": 1.00, "high": 2.0, "low": 0.5, "close": 1.5},
        {"open": 1.60, "high": 2.5, "low": 1.2, "close": 2.2},
        {"open": 2.30, "high": 2.4, "low": 1.0, "close": 1.1},
        {"open": 1.20, "high": 1.3, "low": 0.8, "close": 0.9},
        {"open": 0.95, "high": 1.1, "low": 0.7, "close": 1.0},
        {"open": 1.05, "high": 1.6, "low": 0.9, "close": 1.5},
        {"open": 1.55, "high": 1.7, "low": 1.2, "close": 1.3},
    ])


def test_detect_wyckoff_patterns():
    result = detect_wyckoff_patterns(wyckoff_df())
    assert result is not None
    assert result["pattern"] == "head_and_shoulders"


def test_detect_smc():
    result = detect_smc(smc_df())
    if result is None:
        pytest.skip("smartmoneyconcepts not available")
    assert any("FVG".lower() in r.lower() for r in result["reasons"])  # imbalance detected


def test_compute_confluence():
    df = smc_df()
    result = compute_confluence(df)
    assert "score" in result and "grade" in result
