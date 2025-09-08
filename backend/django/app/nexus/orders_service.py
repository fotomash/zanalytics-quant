from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Tuple, Optional, Dict, Any
import os
import requests


DJANGO_INTERNAL_BASE = os.environ.get("DJANGO_INTERNAL_BASE", "http://django:8000").rstrip("/")


def _normalize_volume(symbol: str, volume: float) -> float:
    """Round down volume to typical broker step/min; conservative defaults if metadata unavailable."""
    # TODO: fetch real symbol meta from bridge if available
    lot_step = 0.01
    min_lot = 0.01
    max_lot = 100.0
    vol = max(min_lot, min(max_lot, float(volume or 0)))
    q = Decimal(str(lot_step))
    vol_norm = float((Decimal(str(vol)) / q).quantize(0, rounding=ROUND_DOWN) * q)
    if vol_norm <= 0:
        vol_norm = float(q)
    return vol_norm


def _post(path: str, json: dict, *, idempotency_key: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    url = f"{DJANGO_INTERNAL_BASE}{path}"
    r = requests.post(url, json=json, headers=headers, timeout=10)
    ok = 200 <= r.status_code < 300
    try:
        body = r.json()
    except Exception:
        body = {"status": r.status_code, "text": r.text}
    return ok, (body if ok else {"error": body, "status": r.status_code})


def place_market_order(symbol: str, volume: float, side: str, sl: float | None = None, tp: float | None = None,
                       comment: Optional[str] = None, *, idempotency_key: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    vol_norm = _normalize_volume(symbol, volume)
    payload = {"symbol": symbol, "volume": vol_norm, "side": side}
    if sl is not None:
        payload["sl"] = float(sl)
    if tp is not None:
        payload["tp"] = float(tp)
    if comment:
        payload["comment"] = comment
    return _post("/api/v1/orders/market", payload, idempotency_key=idempotency_key)


def modify_sl_tp(ticket: int, sl: float | None = None, tp: float | None = None, *, idempotency_key: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    payload: Dict[str, Any] = {"ticket": int(ticket)}
    if sl is not None:
        payload["sl"] = float(sl)
    if tp is not None:
        payload["tp"] = float(tp)
    return _post("/api/v1/orders/modify", payload, idempotency_key=idempotency_key)


def close_position_partial_or_full(ticket: int, *, fraction: float | None = None, volume: float | None = None,
                                   idempotency_key: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    payload: Dict[str, Any] = {"ticket": int(ticket)}
    # prefer absolute volume when provided
    if volume is not None:
        payload["volume"] = float(volume)
    elif fraction is not None:
        payload["fraction"] = float(fraction)
    return _post("/api/v1/orders/close", payload, idempotency_key=idempotency_key)


def get_position(ticket: int) -> Dict[str, Any]:
    try:
        url = f"{DJANGO_INTERNAL_BASE}/api/v1/account/positions"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        for p in r.json():
            try:
                if int(p.get("ticket")) == int(ticket):
                    return p
            except Exception:
                continue
        return {}
    except Exception:
        return {}


def get_account_info() -> Dict[str, Any]:
    try:
        url = f"{DJANGO_INTERNAL_BASE}/api/v1/account/info"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}
