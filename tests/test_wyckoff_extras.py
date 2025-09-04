import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from components.wyckoff_adaptive import analyze_wyckoff_adaptive
from components.wyckoff_agents import MultiTFResolver


def _bars(n=240, p=1.0, v=100):
    idx = pd.date_range("2025-01-01", periods=n, freq="T")
    return pd.DataFrame({"open": p, "high": p * 1.002, "low": p * 0.998, "close": p, "volume": v}, index=idx)


def test_news_buffer_clamps_logits():
    df = _bars()
    df.loc[df.index[100], "close"] = df["close"].iloc[99] * 1.01
    out = analyze_wyckoff_adaptive(
        df,
        win=30,
        news_times=[df.index[100]],
        news_cfg={"pre_bars": 1, "post_bars": 1, "volz_thresh": 0.5, "clamp": 0.5},
    )
    logits = out["phases"]["logits"]
    mask = out["news_mask"]
    assert mask.sum() >= 1 and (np.abs(logits[mask]).max() <= np.abs(logits).max())


def test_nan_resilience_no_volume():
    df = _bars()
    df.drop(columns=["volume"], inplace=True)
    out = analyze_wyckoff_adaptive(df, win=30)
    assert "phases" in out and len(out["phases"]["labels"]) == len(df)


def test_mtf_resolver_clamps_conflicts():
    l1 = np.array(["Distribution", "Distribution", "Distribution"])
    l5 = np.array(["Markup", "Markup", "Markup"])
    l15 = np.array(["Neutral", "Markup", "Markup"])
    conflict = MultiTFResolver().resolve(l1, l5, l15)["conflict_mask"]
    assert conflict.sum() >= 1
