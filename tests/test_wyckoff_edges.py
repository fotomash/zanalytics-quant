import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from components.wyckoff_agents import WyckoffGuard
from components.wyckoff_scorer import WyckoffScorer


def test_guard_suppresses_on_low_conditions():
    labels = np.array(["Distribution", "Accumulation", "Markup"])
    vol_z = np.array([0.0, 0.0, 2.0])
    eff = np.array([0.0, 0.0, 2.0])
    res = WyckoffGuard().suppress(labels, vol_z, eff)
    assert res["suppress_distribution"][0]
    assert res["suppress_accumulation"][1]


def test_scorer_outputs_score_and_probs():
    idx = pd.date_range("2024-01-01", periods=20, freq="T")
    df = pd.DataFrame({"open": 1, "high": 1, "low": 1, "close": 1, "volume": 100}, index=idx)
    out = WyckoffScorer().score(df)
    assert 0.0 <= out["score"] <= 100.0
    assert out["probs"].shape[1] == 4
