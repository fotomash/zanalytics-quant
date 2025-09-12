import importlib.util
from pathlib import Path

import pytest

# Import module directly to avoid executing core.__init__
module_path = Path(__file__).resolve().parents[2] / "core" / "confidence_tracer.py"
spec = importlib.util.spec_from_file_location("confidence_tracer", module_path)
confidence_tracer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(confidence_tracer)
ConfidenceTracer = confidence_tracer.ConfidenceTracer


def test_trace_computes_weighted_score():
    tracer = ConfidenceTracer()
    result = {"raw_calculation": 0.5, "strategy": "ema_bullish"}
    score, debug = tracer.trace("test_agent", result)
    # (0.5 + 0.1) / 1.0 * (1 + 0.1 * 1 condition)
    assert score == pytest.approx(0.66, rel=1e-2)
    assert debug["raw"] == 0.5
    assert debug["simulation_adjustment"] == 0.1
    assert debug["strategy_weight"] == pytest.approx(1.1)


def test_trace_handles_unknown_agent_and_strategy():
    tracer = ConfidenceTracer()
    result = {"raw_calculation": 0.5, "strategy": "unknown"}
    score, debug = tracer.trace("unknown_agent", result)
    assert score == pytest.approx(0.5)
    assert debug["simulation_adjustment"] == 0.0
    assert debug["strategy_weight"] == 1.0
