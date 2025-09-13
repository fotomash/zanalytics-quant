from __future__ import annotations

import numpy as np
import pandas as pd

from utils.enrichment import compute_dss


def test_dss_outputs_are_deterministic():
    df = pd.DataFrame(
        {
            "open": [1, 2, 3, 4, 5],
            "high": [1.1, 2.1, 3.1, 4.1, 5.1],
            "low": [0.9, 1.9, 2.9, 3.9, 4.9],
            "close": [1, 2, 3, 2, 1],
        }
    )
    metrics, vec = compute_dss(df)
    assert metrics["mean_displacement"] == 0.0
    assert metrics["net_shift"] == 0.0
    expected = np.array([[0, 0], [1, 1], [1, 1], [-1, -1], [-1, -1]], dtype=float)
    assert np.array_equal(vec, expected)

    # Second call should produce identical results
    metrics2, vec2 = compute_dss(df)
    assert metrics == metrics2
    assert np.array_equal(vec, vec2)


def test_dss_empty_dataframe():
    df = pd.DataFrame(columns=["open", "high", "low", "close"])
    metrics, vec = compute_dss(df)
    assert metrics == {}
    assert vec.size == 0
