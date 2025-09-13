import logging
import pytest

from risk_enforcer import EnhancedRiskEnforcer


def _build_enforcer():
    enforcer = EnhancedRiskEnforcer()
    # Mirror core state for direct method access
    enforcer.limits = enforcer.core.limits
    enforcer.daily_stats = enforcer.core.daily_stats
    enforcer.behavioral_flags = enforcer.core.behavioral_flags
    enforcer.state = enforcer.core.state
    return enforcer


def test_check_daily_profit_target_logs_and_raises(caplog):
    enforcer = _build_enforcer()
    enforcer.limits["daily_profit_target_usd"] = 100
    enforcer.daily_stats["total_pnl"] = "bad"  # force float conversion error
    with caplog.at_level(logging.ERROR, logger="risk_enforcer"):
        with pytest.raises(Exception):
            enforcer._check_daily_profit_target()
    assert "Daily profit target check failed" in caplog.text


def test_allow_surfaces_profit_target_exception(caplog):
    enforcer = _build_enforcer()
    enforcer.limits["daily_profit_target_usd"] = 100
    enforcer.daily_stats["total_pnl"] = "bad"
    signal = {"sod_equity": 1000}
    with caplog.at_level(logging.ERROR, logger="risk_enforcer"):
        with pytest.raises(Exception):
            enforcer.allow(signal)
    assert "Daily profit target check failed" in caplog.text
