from __future__ import annotations

import os
from typing import Any, Dict, Tuple, Optional

import requests

# Direct MT5 bridge endpoint
MT5_API_URL = os.environ.get("MT5_API_URL", "http://mt5:5001").rstrip("/")


def modify_position(ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> Tuple[bool, Dict[str, Any]]:
    """Modify SL/TP for a position via the MT5 bridge.

    Returns (ok, result) where ok indicates HTTP 2xx from the bridge.
    Fields with value ``None`` are omitted to keep existing broker values.
    """
    # The MT5 API requires the symbol for the ticket. Fetch the current
    # positions and locate the matching ticket to obtain its symbol.
    try:
        pos_resp = requests.get(f"{MT5_API_URL}/positions_get", timeout=5)
        positions = pos_resp.json() if pos_resp.status_code == 200 else []
        symbol: Optional[str] = None
        for p in positions or []:
            try:
                if int(p.get("ticket")) == int(ticket):
                    symbol = p.get("symbol")
                    break
            except Exception:
                continue
        if not symbol:
            return False, {"error": f"position {ticket} not found"}
    except Exception as e:
        return False, {"error": str(e)}

    payload: Dict[str, Any] = {"ticket": int(ticket), "symbol": symbol}
    if sl is not None:
        payload["sl"] = float(sl)
    if tp is not None:
        payload["tp"] = float(tp)
    url = f"{MT5_API_URL}/modify_sl_tp"
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
