import os
import sys

from fastapi.testclient import TestClient

# Ensure repo root on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def test_pyrest_metrics_endpoint_exposes_counters():
    os.environ["PULSE_SKIP_MT5_CONNECT"] = "1"
    from services.pyrest.app import app

    client = TestClient(app)
    # trigger a request so middleware records metrics
    client.get("/pulse/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "pyrest_request_latency_seconds" in body
    assert "pyrest_request_count_total" in body
    assert "pyrest_kernel_status" in body
    assert "pyrest_risk_decisions_total" in body
    assert "pyrest_rate_limit_events_total" in body
