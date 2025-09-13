import pandas as pd

from core.microstructure_filter import apply_microstructure_filter


def test_apply_microstructure_filter_removes_invalid_ticks():
    df = pd.DataFrame(
        {
            "bid": [100.0, 100.5, 101.0, 100.2],
            "ask": [100.1, 100.4, 100.9, 100.7],
            "volume": [10, 0, 5, 8],
        }
    )

    filtered = apply_microstructure_filter(df, max_spread=0.3)

    assert len(filtered) == 1
    assert filtered.iloc[0]["bid"] == 100.0
    assert filtered.iloc[0]["ask"] == 100.1
