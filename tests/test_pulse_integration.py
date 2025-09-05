import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pulse_kernel import PulseKernel


@pytest.mark.integration
def test_full_pipeline_allows_when_safe():
    k = PulseKernel("pulse_config.yaml")
    frame = {
        "ts": "2025-01-15T10:31:00Z",
        "symbol": "EURUSD",
        "bars": [{"open": 1.0850, "high": 1.0862, "low": 1.0845, "close": 1.0858, "volume": 1200}],
    }
    out = k.on_frame(frame)
    assert out["decision"]["status"] in {"allowed", "warned"}
    assert isinstance(out["score"]["score"], (int, float))

