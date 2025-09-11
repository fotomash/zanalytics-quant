import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from pulse_kernel import PulseKernel


def test_kernel_status():
    k = PulseKernel("pulse_config.yaml")
    st = k.get_status()
    assert "behavioral_state" in st


def test_decision_path():
    k = PulseKernel("pulse_config.yaml")
    res = asyncio.run(k.on_frame({"symbol": "EURUSD", "tf": "M15", "df": {}}))
    assert "action" in res
