import os
import sys

from fastapi.testclient import TestClient

# Ensure repo root on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def test_metrics_endpoint_exposes_counters():
    os.environ["PULSE_API_KEY"] = "test-key"
    from services.pulse_api.main import app

    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "pulse_request_latency_seconds" in body
    assert "pulse_request_errors_total" in body
    assert "pulse_score_evaluations_total" in body
    assert "pulse_risk_evaluations_total" in body
