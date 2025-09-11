import pandas as pd
import pytest

from core.smc_analyzer import SMCAnalyzer


def _sample_df(rows: int = 60) -> pd.DataFrame:
    data = []
    for i in range(rows):
        if i == 20:
            data.append({"open": 1.0, "high": 1.1, "low": 0.8, "close": 0.9})
        else:
            data.append({"open": 1.0, "high": 1.1, "low": 0.8, "close": 1.0})
    return pd.DataFrame(data)


def test_identify_liquidity_zones():
    df = _sample_df()
    analyzer = SMCAnalyzer()
    zones = analyzer.identify_liquidity_zones(df, lookback=50)
    assert zones, "Expected at least one liquidity zone"
    assert all("type" in z for z in zones)


def test_identify_order_blocks():
    df = _sample_df()
    analyzer = SMCAnalyzer()
    blocks = analyzer.identify_order_blocks(df)
    assert blocks, "Expected at least one order block"
    assert all("type" in b for b in blocks)


def test_analyze():
    df = _sample_df()
    analyzer = SMCAnalyzer()
    expected_lz = analyzer.identify_liquidity_zones(df, lookback=50)
    expected_ob = analyzer.identify_order_blocks(df)
    results = analyzer.analyze(df)
    expected_keys = {
        "liquidity_zones",
        "order_blocks",
        "fair_value_gaps",
        "market_structure",
        "liquidity_sweeps",
        "displacement",
        "inducement",
    }
    assert expected_keys.issubset(results.keys())
    assert results["liquidity_zones"] == expected_lz
    assert results["order_blocks"] == expected_ob
