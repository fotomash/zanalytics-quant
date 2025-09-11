import json
import os
from datetime import timedelta
from typing import Any, Dict

import logging
import redis  # type: ignore
import requests


# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TTL_DEFAULTS: Dict[str, int] = {
    "session_boot": int(os.getenv("SESSION_BOOT_TTL", "30")),
    "trades_recent": int(os.getenv("TRADES_RECENT_TTL", "15")),
    "risk_status": int(os.getenv("RISK_STATUS_TTL", "20")),
}

logger = logging.getLogger(__name__)
r = redis.Redis.from_url(REDIS_URL)


def _get_cache_key(api_type: str, user_id: str = "default") -> str:
    return f"{api_type}:{user_id}"


def _fetch_with_cache(api_url: str, token: str | None, api_type: str, payload: Dict[str, Any] | None = None, user_id: str = "default") -> Dict[str, Any]:
    """Generic cached fetch for ActionBus queries and state snapshot."""
    cache_key = _get_cache_key(api_type, user_id)
    ttl = int(TTL_DEFAULTS.get(api_type, 30))

    # 1) Try cache
    try:
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        logger.warning("Error retrieving cache key %s", cache_key, exc_info=True)

    # 2) API call
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if api_type == "risk_status":
        resp = requests.get(f"{api_url.rstrip('/')}/api/v1/state/snapshot", headers=headers, timeout=10)
    else:
        body = {"type": api_type, "payload": payload or {}}
        resp = requests.post(f"{api_url.rstrip('/')}/api/v1/actions/query", headers=headers, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # 3) Cache result
    try:
        r.setex(cache_key, timedelta(seconds=ttl), json.dumps(data))
    except Exception:
        logger.warning("Error setting cache key %s", cache_key, exc_info=True)

    return data


# Public helpers
def fetch_session_boot(api_url: str, token: str | None = None, user_id: str = "default") -> Dict[str, Any]:
    payload = {
        "limit_trades": 10,
        "include_positions": True,
        "include_equity": True,
        "include_risk": True,
    }
    return _fetch_with_cache(api_url, token, "session_boot", payload, user_id)


def fetch_trades_recent(api_url: str, token: str | None = None, limit: int = 50, user_id: str = "default") -> Dict[str, Any]:
    payload = {"limit": int(limit)}
    return _fetch_with_cache(api_url, token, "trades_recent", payload, user_id)


def fetch_risk_status(api_url: str, token: str | None = None, user_id: str = "default") -> Dict[str, Any]:
    return _fetch_with_cache(api_url, token, "risk_status", None, user_id)


def fetch_cached(api_url: str, token: str | None, api_type: str, payload: Dict[str, Any] | None = None, user_id: str = "default") -> Dict[str, Any]:
    """Unified cached fetch across supported API types.

    api_type ∈ { 'session_boot', 'trades_recent', 'risk_status' }
    """
    return _fetch_with_cache(api_url, token, api_type, payload, user_id)
