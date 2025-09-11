import json
import fakeredis

from risk_management.behavioral_risk_enforcer import BehavioralRiskEnforcer


POLICIES = {
    "behavioral_rules": {
        "discipline_score": {"threshold": 0.4, "reduce_max_lot_size_by": 0.5},
        "patience_index": {"threshold": 0.2, "enforce_cooldown_period": 15},
        "daily_drawdown": {"threshold": 0.03, "block_new_trades": True},
    }
}


def test_discipline_reduces_lot(tmp_path):
    (tmp_path / "policies.yaml").write_text(json.dumps(POLICIES))
    enforcer = BehavioralRiskEnforcer(
        redis_client=fakeredis.FakeStrictRedis(decode_responses=True),
        policies_path=str(tmp_path / "policies.yaml"),
    )
    enforcer.redis.set("behavioral_metrics", json.dumps({"discipline_score": 0.3}))
    allowed, order, messages = enforcer.enforce({"quantity": 100})
    assert allowed
    assert order["quantity"] == 50
    assert any("discipline" in m.lower() for m in messages)


def test_patience_triggers_cooldown(tmp_path):
    (tmp_path / "policies.yaml").write_text(json.dumps(POLICIES))
    enforcer = BehavioralRiskEnforcer(
        redis_client=fakeredis.FakeStrictRedis(decode_responses=True),
        policies_path=str(tmp_path / "policies.yaml"),
    )
    enforcer.redis.set("behavioral_metrics", json.dumps({"patience_index": 0.1}))
    allowed, _, messages = enforcer.enforce({"quantity": 100})
    assert not allowed
    assert any("cooling-off period" in m.lower() for m in messages)


def test_drawdown_blocks(tmp_path):
    (tmp_path / "policies.yaml").write_text(json.dumps(POLICIES))
    enforcer = BehavioralRiskEnforcer(
        redis_client=fakeredis.FakeStrictRedis(decode_responses=True),
        policies_path=str(tmp_path / "policies.yaml"),
    )
    enforcer.redis.set("behavioral_metrics", json.dumps({"daily_drawdown": 0.04}))
    allowed, _, messages = enforcer.enforce({"quantity": 100})
    assert not allowed
    assert any("drawdown" in m.lower() for m in messages)
