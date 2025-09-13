import pandas as pd
from utils.microstructure_filter import microstructure_filter


def test_microstructure_filter_removes_wide_spread_or_low_liquidity():
    df = pd.DataFrame(
        {
            "spread": [0.01, 0.10, 0.03],
            "liquidity_score": [1.2, 0.2, 1.5],
            "mid_price": [100.0, 101.0, 102.0],
        }
    )

    filtered = microstructure_filter(df, max_spread=0.05, min_liquidity=1.0)

    assert len(filtered) == 2
    assert filtered["spread"].max() <= 0.05
    assert filtered["liquidity_score"].min() >= 1.0
