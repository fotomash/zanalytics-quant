"""Tests for :mod:`integration.bootstrap_os_integration`."""

from __future__ import annotations

from typing import Dict

import fakeredis

from integration.bootstrap_os_integration import (
    bootstrap_all,
    initialize_ml_bridge,
    initialize_risk_enforcer,
)


def test_initialize_risk_enforcer_singleton() -> None:
    """Risk enforcer should only be initialised once."""

    first = initialize_risk_enforcer()
    second = initialize_risk_enforcer()
    assert first is second
    assert hasattr(first, "check_trade")


def test_initialize_ml_bridge_uses_client() -> None:
    """Provided Redis client should be used by the bridge."""

    fake: fakeredis.FakeRedis = fakeredis.FakeRedis()
    bridge = initialize_ml_bridge(redis_client=fake)
    assert bridge.redis_client is fake


def test_bootstrap_all_returns_instances() -> None:
    """Combined bootstrap should yield both instances."""

    fake: fakeredis.FakeRedis = fakeredis.FakeRedis()
    # Ensure bridge initialised with our fake client
    bridge = initialize_ml_bridge(redis_client=fake)
    result: Dict[str, object] = bootstrap_all()
    assert "risk_enforcer" in result and "ml_bridge" in result
    assert result["ml_bridge"] is bridge

