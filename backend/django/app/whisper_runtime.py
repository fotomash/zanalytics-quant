from __future__ import annotations

import json
import os
import time
from typing import List, Dict, Any

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

_inmem: List[Dict[str, Any]] = []


def _redis() -> "redis.Redis | None":  # type: ignore
    if redis is None:
        return None
    url = os.getenv("REDIS_URL")
    if url:
        try:
            return redis.from_url(url)
        except Exception:
            return None
    try:
        return redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)))
    except Exception:
        return None


def latest_whispers(limit: int = 50) -> List[Dict[str, Any]]:
    r = _redis()
    if r is None:
        return list(reversed(_inmem[-limit:]))
    try:
        items = r.lrange("whispers", -limit, -1) or []
        out: List[Dict[str, Any]] = []
        for b in items:
            try:
                out.append(json.loads(b))
            except Exception:
                continue
        return out
    except Exception:
        return []


def ack_whisper(body: bytes) -> Dict[str, Any]:
    try:
        data = json.loads(body or b"{}")
    except Exception:
        data = {}
    data = data or {}
    rec = {
        "ts": time.time(),
        "id": data.get("id"),
        "reason": data.get("reason"),
        "type": "ack",
    }
    r = _redis()
    if r is None:
        _inmem.append({"ack": rec})
        _inmem.append({"log": rec})
        return {"ok": True}
    try:
        r.rpush("whisper-acks", json.dumps(rec))
        r.rpush("whisper-log", json.dumps({"ts": rec["ts"], "text": f"ACK: {rec.get('id','')} – {rec.get('reason','')}"}))
        return {"ok": True}
    except Exception:
        return {"ok": False}


def act_on_whisper(body: bytes) -> Dict[str, Any]:
    try:
        data = json.loads(body or b"{}")
    except Exception:
        data = {}
    data = data or {}
    rec = {
        "ts": time.time(),
        "id": data.get("id"),
        "action": data.get("action"),
        "type": "act",
    }
    r = _redis()
    if r is None:
        _inmem.append({"act": rec})
        _inmem.append({"log": rec})
        return {"ok": True}
    try:
        r.rpush("whisper-actions", json.dumps(rec))
        label = rec.get('action') or 'act'
        r.rpush("whisper-log", json.dumps({"ts": rec["ts"], "text": f"ACT: {rec.get('id','')} – {label}"}))
        return {"ok": True}
    except Exception:
        return {"ok": False}
