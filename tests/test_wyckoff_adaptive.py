import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from components.wyckoff_adaptive import analyze_wyckoff_adaptive


def test_analyze_wyckoff_adaptive_basic():
    idx = pd.date_range("2025-01-01", periods=60, freq="T")
    df = pd.DataFrame(
        {
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 100,
        },
        index=idx,
    )
    out = analyze_wyckoff_adaptive(df, win=30)
    assert "phases" in out and len(out["phases"]["labels"]) == len(df)

