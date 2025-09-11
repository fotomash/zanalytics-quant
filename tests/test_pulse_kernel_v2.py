import json

from integration.pulse_kernel_v2 import MLSignalAdapter, PulseKernelV2
from pulse_kernel import PulseKernel


def test_model_signal_influences_decision_and_journal(tmp_path):
    """High scoring signals trigger trade action and are journaled."""
    data = {"score": 80}
    model_file = tmp_path / "model.json"
    model_file.write_text(json.dumps(data))

    output = MLSignalAdapter.from_file(str(model_file))
    journal = []
    kernel = PulseKernel()
    adapter = PulseKernelV2(kernel, journal_hook=journal.append)

    decision = adapter.process_model_output(output)

    assert decision["action"] == "trade"
    assert journal and journal[0]["score"] == data["score"]


def test_risk_check_blocks_signal(tmp_path):
    """Risk limits block trading even for strong signals."""
    data = {"score": 90}
    model_file = tmp_path / "model.json"
    model_file.write_text(json.dumps(data))
    output = MLSignalAdapter.from_file(str(model_file))

    kernel = PulseKernel()
    adapter = PulseKernelV2(kernel)

    # Force daily loss limit breach to trigger risk block
    adapter.risk.limits["daily_loss_limit"] = 100
    adapter.risk.daily_stats["total_pnl"] = -200

    decision = adapter.process_model_output(output)

    assert decision["approved"] is False
    assert decision["action"] == "hold"
