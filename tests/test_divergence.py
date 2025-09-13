import pandas as pd
from indicators.basic import rsi


def _bearish_divergence(df: pd.DataFrame) -> bool:
    rsi_values = rsi.calculate(df, period=2).iloc[:, 0]
    highs = [
        i
        for i in range(1, len(df) - 1)
        if df.close[i] > df.close[i - 1] and df.close[i] > df.close[i + 1]
    ]
    if len(highs) < 2:
        return False
    h1, h2 = highs[-2], highs[-1]
    return df.close[h2] > df.close[h1] and rsi_values[h2] < rsi_values[h1]


def test_rsi_bearish_divergence_detected():
    prices = [1, 2, 3, 2.5, 3.5, 3.2]
    df = pd.DataFrame({"close": prices})
    assert _bearish_divergence(df)
