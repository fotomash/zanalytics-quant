import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pulse_kernel import PulseKernel


def test_pulse_kernel_on_frame_basic():
    kernel = PulseKernel()
    frame = {
        "ts": 0,
        "symbol": "EURUSD",
        "bars": [
            {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 100}
        ],
    }
    out = kernel.on_frame(frame)
    assert "score" in out and "decision" in out
