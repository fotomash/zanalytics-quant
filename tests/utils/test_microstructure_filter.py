import pandas as pd

from utils.microstructure_filter import microstructure_filter


def test_microstructure_filter_removes_wide_spreads():
    df = pd.DataFrame(
        {
            "bid": [1.0, 1.0, 1.0],
            "ask": [1.0001, 1.5, 1.0001],
            "volume": [10, 10, 10],
        }
    )

    filtered = microstructure_filter(df, max_spread=0.001)

    assert len(filtered) == 2
    assert filtered["ask"].max() < 1.5
