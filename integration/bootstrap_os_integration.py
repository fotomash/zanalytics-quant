"""Startup hooks for ML and risk enforcement integration.

This module provides lightweight helper functions that bootstrap the
components required by various parts of the analytics stack.  Downstream
modules can import and call these helpers during their own start-up phase to
obtain ready-to-use instances of the ML bridge and risk enforcer.

The functions are deliberately small wrappers around the underlying objects
and cache their results so that initialisation only happens once per process.
This mirrors the behaviour of many ``bootstrap`` style modules in larger
applications and keeps the rest of the codebase free from global imports.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from components.risk_enforcer import RiskEnforcer
from integration.redis_ml_bridge import RedisMLBridge


_risk_enforcer: Optional[RiskEnforcer] = None
_ml_bridge: Optional[RedisMLBridge] = None


def initialize_risk_enforcer(config_path: str = "pulse_config.yaml") -> RiskEnforcer:
    """Initialise and return a :class:`RiskEnforcer` instance.

    Parameters
    ----------
    config_path:
        Path to the YAML configuration file containing risk limits.  The
        default mirrors the configuration file used by the rest of the
        project.

    Returns
    -------
    RiskEnforcer
        The singleton :class:`RiskEnforcer` used for behavioural and risk
        checks.
    """

    global _risk_enforcer
    if _risk_enforcer is None:
        _risk_enforcer = RiskEnforcer(config_path=config_path)
    return _risk_enforcer


def initialize_ml_bridge(
    redis_url: str = "redis://localhost:6379/0",
    input_channel: str = "model:outputs",
    output_channel: str = "signals",
    retry_interval: float = 1.0,
    redis_client: Optional[Any] = None,
) -> RedisMLBridge:
    """Create a :class:`RedisMLBridge` instance.

    Parameters
    ----------
    redis_url:
        Connection URL for the Redis instance.
    input_channel:
        Pub/Sub channel from which raw model output will be consumed.
    output_channel:
        Channel to which structured signals are published.
    retry_interval:
        Delay (in seconds) between connection retries.
    redis_client:
        Optional pre-created Redis client, primarily useful for testing with
        objects such as ``fakeredis.FakeRedis``.

    Returns
    -------
    RedisMLBridge
        The singleton bridge instance used to translate ML outputs into
        structured signals.
    """

    global _ml_bridge
    if _ml_bridge is None:
        _ml_bridge = RedisMLBridge(
            redis_url=redis_url,
            input_channel=input_channel,
            output_channel=output_channel,
            retry_interval=retry_interval,
            redis_client=redis_client,
        )
    return _ml_bridge


def bootstrap_all(**kwargs: Any) -> Dict[str, Any]:
    """Initialise ML and risk enforcement components.

    This is a convenience wrapper that initialises both the risk enforcer and
    the ML bridge.  Keyword arguments are forwarded to the respective
    initialiser functions.

    Parameters
    ----------
    **kwargs:
        Keyword arguments compatible with
        :func:`initialize_risk_enforcer` and
        :func:`initialize_ml_bridge`.

    Returns
    -------
    dict
        Mapping containing the created ``risk_enforcer`` and ``ml_bridge``
        instances.
    """

    risk = initialize_risk_enforcer(kwargs.get("config_path", "pulse_config.yaml"))
    bridge = initialize_ml_bridge(
        redis_url=kwargs.get("redis_url", "redis://localhost:6379/0"),
        input_channel=kwargs.get("input_channel", "model:outputs"),
        output_channel=kwargs.get("output_channel", "signals"),
        retry_interval=kwargs.get("retry_interval", 1.0),
        redis_client=kwargs.get("redis_client"),
    )
    return {"risk_enforcer": risk, "ml_bridge": bridge}


__all__ = ["initialize_risk_enforcer", "initialize_ml_bridge", "bootstrap_all"]

