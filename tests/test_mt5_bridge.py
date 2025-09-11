from datetime import datetime

import logging
import pandas as pd
import pytest
import requests

from mt5_bridge import MT5Bridge


def _sample_history_df():
    return pd.DataFrame([
        {
            "time": datetime.utcnow(),
            "ticket": 1,
            "symbol": "EURUSD",
            "volume": 1.0,
            "profit": 10.0,
            "revenge_trade": False,
            "overconfidence": False,
            "fatigue_trade": False,
            "fomo_trade": False,
            "behavioral_risk_score": 0,
        }
    ])


def test_connect_initialization_failure_logs_error(monkeypatch, caplog):
    bridge = MT5Bridge()
    monkeypatch.setattr("mt5_bridge.mt5.initialize", lambda: False)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="MT5 initialization failed"):
            bridge.connect()

    assert "MT5 initialization failed" in caplog.text


def test_sync_to_pulse_journal_api_logs_error(monkeypatch, caplog):
    bridge = MT5Bridge()
    monkeypatch.setattr(MT5Bridge, "get_real_trade_history", lambda self: _sample_history_df())
    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(requests, "post", fake_post)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="Failed to sync journal to API"):
            bridge.sync_to_pulse_journal_api("http://example.com", "token")

    assert "Failed to sync journal to API" in caplog.text
