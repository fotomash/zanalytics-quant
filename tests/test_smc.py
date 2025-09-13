import pandas as pd
import numpy as np
from core.smc_analyzer import SMCAnalyzer


def test_detects_liquidity_sweep():
    """SMC analyzer flags a buy-side liquidity grab with reversal."""
    n = 80
    df = pd.DataFrame(
        {
            "open": np.full(n, 100.0),
            "high": np.full(n, 100.0),
            "low": np.full(n, 99.0),
            "close": np.full(n, 99.5),
        }
    )
    # engineer a sweep above repeated highs then close back below the level
    df.loc[61, "high"] = 101.0
    for i in range(61, n):
        df.loc[i, "close"] = 99.4
    df.loc[n - 1, "close"] = 99.0

    sweeps = SMCAnalyzer().detect_liquidity_sweeps(df)
    assert any(s["type"] == "buy_side_sweep" for s in sweeps)
