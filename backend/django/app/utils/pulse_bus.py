"""
Pulse event bus helpers (Redis-first).

Lightweight publish functions that write both a latest key and append to a stream.
Keeps contracts small and stable; callers pass plain dicts.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Any

import redis


def _client() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    return redis.from_url(url, decode_responses=True)


def _safe_json(d: Dict[str, Any]) -> str:
    try:
        return json.dumps(d, ensure_ascii=False)
    except Exception:
        return "{}"


def publish_risk_summary(summary: Dict[str, Any]) -> None:
    """Publish risk summary to key + stream.

    Keys:
      - pulse:risk:latest (string JSON)
      - stream pulse:risk (XADD)
    """
    r = _client()
    js = _safe_json(summary)
    try:
        r.set("pulse:risk:latest", js, ex=30)
    except Exception:
        pass
    try:
        r.xadd("pulse:risk", summary, maxlen=500, approximate=True)
    except Exception:
        pass


def publish_decision(decision: Dict[str, Any]) -> None:
    r = _client()
    js = _safe_json(decision)
    try:
        r.set("pulse:decision:latest", js, ex=30)
    except Exception:
        pass
    try:
        r.xadd("pulse:decisions", decision, maxlen=500, approximate=True)
    except Exception:
        pass


def publish_session_state(state: Dict[str, Any]) -> None:
    r = _client()
    js = _safe_json(state)
    try:
        r.set("pulse:session:latest", js, ex=60)
    except Exception:
        pass
    try:
        r.xadd("pulse:session", state, maxlen=500, approximate=True)
    except Exception:
        pass


def publish_journal_entry(entry: Dict[str, Any]) -> None:
    r = _client()
    try:
        r.xadd("pulse:journal", entry, maxlen=1000, approximate=True)
    except Exception:
        pass

