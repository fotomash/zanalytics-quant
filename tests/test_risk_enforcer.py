import sys
from pathlib import Path
import datetime as dt

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from components.risk_enforcer import RiskEnforcer


@pytest.fixture
def enforcer(tmp_path):
    cfg = tmp_path / "pulse_config.yaml"
    cfg.write_text("""
DAILY_MAX_LOSS: 500
RISK_PER_TRADE: 0.01
MAX_TRADES_PER_DAY: 5
COOLDOWN_AFTER_LOSS: 15
""")
    return RiskEnforcer(config_path=str(cfg))


def test_daily_limit_breach(enforcer):
    enforcer.trade_history = [{"pnl": -400, "date": dt.date.today(), "time": dt.datetime.now()}]
    result = enforcer.check_trade({"risk": 200, "account_balance": 10_000})
    assert result["decision"] == "blocked"
    assert "Daily limit exceeded" in result["reasons"]


def test_cooldown_warning(enforcer):
    enforcer.trade_history = [{"pnl": -100, "date": dt.date.today(), "time": dt.datetime.now() - dt.timedelta(minutes=5)}]
    result = enforcer.check_trade({"risk": 50, "account_balance": 10_000})
    assert result["decision"] == "warning"
    assert any("Cooldown" in r for r in result["reasons"])
