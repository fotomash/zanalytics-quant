import pandas as pd
import sys
from pathlib import Path
import asyncio
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pulse_kernel import PulseKernel


def _bars(n=60, p=1.0, v=100):
    idx = pd.date_range("2025-01-01", periods=n, freq="T")
    return [
        {
            "ts": str(idx[i]),
            "open": p,
            "high": p * 1.001,
            "low": p * 0.999,
            "close": p,
            "volume": v,
        }
        for i in range(n)
    ]


@pytest.mark.xfail(reason="PulseKernel does not implement news blocking yet")
def test_kernel_news_blocks():
    k = PulseKernel("pulse_config.yaml")
    frame = {
        "ts": "2025-01-01T00:59:00Z",
        "symbol": "EURUSD",
        "bars": _bars(10),
        "features": {"news_active": True},
    }
    out = asyncio.run(k.on_frame(frame))
    assert out["action"] == "blocked"
    assert any("news" in r.lower() for r in out["reasons"])


def test_kernel_mtf_clamps_score():
    k = PulseKernel("pulse_config.yaml")
    f1 = {"ts": "2025-01-01T00:59:00Z", "symbol": "EURUSD", "bars": _bars(60)}
    f1["bars_m5"] = f1["bars"]
    f1["bars_m15"] = f1["bars"]
    before = asyncio.run(k.on_frame({"ts": f1["ts"], "symbol": f1["symbol"], "bars": f1["bars"]}))
    before_score = before.get("confidence", 0)
    after_score = asyncio.run(k.on_frame(f1)).get("confidence", 0)
    assert after_score <= before_score

