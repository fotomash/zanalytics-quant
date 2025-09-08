from __future__ import annotations

import json
from typing import Dict, Any

from django.conf import settings

from ..views import _redis_client  # reuse existing redis helper
from .gates import (
    context_gate,
    liquidity_gate,
    structure_gate,
    imbalance_gate,
    risk_gate,
    confluence_gate,
)


def _load_minute_data(symbol: str) -> Dict[str, Any]:
    """Placeholder: Return dict of dataframes keyed by timeframe.

    Implement by wiring to your existing data loaders. For now, returns empty.
    """
    return {"H4": None, "H1": None, "M15": None, "M1": None}


def pulse_status(symbol: str) -> Dict[str, int]:
    """Compute gate status for the given symbol and cache briefly in Redis.

    Returns a dict of 0/1 flags: context, liquidity, structure, imbalance, risk, confluence.
    """
    data = _load_minute_data(symbol)

    ctx = context_gate(data.get("H4"))  # or combine H4/H1
    liq = liquidity_gate(data.get("M15"))
    struct = structure_gate(data.get("M1"))
    imb = imbalance_gate(data.get("M1"))
    rsk = risk_gate(imb, struct)
    conf = confluence_gate(data)

    status = {
        "context": int(bool(ctx.get("passed"))),
        "liquidity": int(bool(liq.get("passed"))),
        "structure": int(bool(struct.get("passed"))),
        "imbalance": int(bool(imb.get("passed"))),
        "risk": int(bool(rsk.get("passed"))),
        "confluence": int(bool(conf.get("passed"))),
    }

    # Cache to Redis with very short TTL
    r = _redis_client()
    try:
        if r is not None:
            key_sym = f"pulse_status:{symbol}"
            r.setex(key_sym, 5, json.dumps(status))
            # Also write a generic key for dashboards not passing symbol yet
            r.setex("pulse:status", 5, json.dumps(status))
    except Exception:
        pass

    return status

