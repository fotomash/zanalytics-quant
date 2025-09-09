from __future__ import annotations

import os
from typing import Any, Dict, Tuple, Optional

import requests

DJANGO_INTERNAL_BASE = os.environ.get("DJANGO_INTERNAL_BASE", "http://django:8000").rstrip("/")


def modify_position(ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> Tuple[bool, Dict[str, Any]]:
    """Modify SL/TP for a position via the MT5 bridge.

    Returns (ok, result) where ok indicates HTTP 2xx from the bridge.
    Fields with value ``None`` are omitted to keep existing broker values.
    """
    payload: Dict[str, Any] = {"ticket": int(ticket)}
    if sl is not None:
        payload["sl"] = float(sl)
    if tp is not None:
        payload["tp"] = float(tp)
    url = f"{DJANGO_INTERNAL_BASE}/api/v1/orders/modify"
    try:
        r = requests.post(url, json=payload, timeout=10)
    except Exception as e:
        return False, {"error": str(e)}
    ok = 200 <= r.status_code < 300
    try:
        body = r.json()
    except Exception:
        body = {"status": r.status_code, "text": r.text}
    return ok, (body if ok else {"error": body, "status": r.status_code})
