import os
import sys
import time
from datetime import datetime

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.pulse_kernel import PulseKernel


def test_mt5_to_kernel_precision() -> None:
    """Verify precision through the stack using real MT5 data if available."""
    try:
        kernel = PulseKernel()
        kernel.connect_mt5()
    except Exception as exc:  # pragma: no cover - environment without MT5
        pytest.skip(f"MT5 unavailable: {exc}")

    result = kernel.process_tick("EURUSD")
    assert "timestamp" in result
    ts = datetime.fromisoformat(result["timestamp"])
    assert ts.tzinfo is not None

    score1 = kernel.process_tick("EURUSD")
    time.sleep(0.1)
    score2 = kernel.process_tick("EURUSD")
    assert abs(score1["score"] - score2["score"]) < 5

    assert 0 <= result["components"]["smc"] <= 100
    assert 0 <= result["components"]["wyckoff"] <= 100
    assert 0 <= result["components"]["ta"] <= 100
