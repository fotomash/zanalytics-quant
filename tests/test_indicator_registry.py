from __future__ import annotations

import pandas as pd

from indicators.registry import disable_indicator, enable_indicator
from core.context_analyzer import ContextAnalyzer


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": range(20),
            "high": [x + 0.5 for x in range(20)],
            "low": [x - 0.5 for x in range(20)],
            "close": range(20),
            "volume": [100] * 20,
        }
    )


def test_enable_disable_indicator() -> None:
    df = _sample_df()
    analyzer = ContextAnalyzer()

    # phase enabled by default
    assert "phase" in analyzer.analyze(df)

    disable_indicator("phase")
    assert "phase" not in analyzer.analyze(df)

    enable_indicator("phase")
    assert "phase" in analyzer.analyze(df)
