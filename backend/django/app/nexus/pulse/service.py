from __future__ import annotations

import json
from typing import Dict, Any
import pandas as pd

from django.conf import settings

from ..views import _redis_client  # reuse existing redis helper
from app.nexus.models import Bar
from app.utils.constants import MT5Timeframe
from app.utils.api.data import fetch_bars
from .gates import (
    context_gate,
    liquidity_gate,
    structure_gate,
    imbalance_gate,
    risk_gate,
    confluence_gate,
)


def _normalize_bars(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    # Ensure expected columns
    cols = {c.lower(): c for c in df.columns}
    # Map time -> timestamp
    if 'time' in cols:
        df['timestamp'] = pd.to_datetime(df[cols['time']])
    elif 'timestamp' in cols:
        df['timestamp'] = pd.to_datetime(df[cols['timestamp']])
    else:
        return None
    for c in ['open', 'high', 'low', 'close']:
        if c in cols:
            df[c] = pd.to_numeric(df[cols[c]], errors='coerce')
        else:
            return None
    # Volume preference: real_volume -> tick_volume -> volume
    vol = None
    if 'real_volume' in cols:
        vol = df[cols['real_volume']]
    elif 'tick_volume' in cols:
        vol = df[cols['tick_volume']]
    elif 'volume' in cols:
        vol = df[cols['volume']]
    else:
        vol = 0
    df['volume'] = pd.to_numeric(vol, errors='coerce').fillna(0)
    # Sort ascending by timestamp and keep only needed columns
    df = df.sort_values('timestamp')
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()


def _load_minute_data(symbol: str) -> Dict[str, Any]:
    """Load H4/H1/M15/M1 bars for a symbol from DB; fallback to bridge.

    Returns dict of pandas DataFrames with columns: timestamp, open, high, low, close, volume.
    """
    out: Dict[str, Any] = {"H4": None, "H1": None, "M15": None, "M1": None}
    tf_map = {
        'H4': ('H4', MT5Timeframe.H4, 300),
        'H1': ('H1', MT5Timeframe.H1, 600),
        'M15': ('M15', MT5Timeframe.M15, 800),
        'M1': ('M1', MT5Timeframe.M1, 1200),
    }
    for key, (db_tf, api_tf, limit) in tf_map.items():
        df: pd.DataFrame | None = None
        # Try DB first
        try:
            qs = Bar.objects.filter(symbol=symbol, timeframe=db_tf).order_by('-time')[:limit]
            if qs:
                import pandas as _p
                df = _p.DataFrame(list(qs.values('time', 'open', 'high', 'low', 'close', 'real_volume', 'tick_volume')))
                # Rename to expected keys
                df = df.rename(columns={'time': 'timestamp'})
                if 'real_volume' in df.columns:
                    df['volume'] = df['real_volume']
                elif 'tick_volume' in df.columns:
                    df['volume'] = df['tick_volume']
        except Exception:
            df = None
        # Fallback to MT5 bridge
        if df is None or df.empty:
            try:
                fb = fetch_bars(symbol, api_tf, limit=limit)
                df = fb
            except Exception:
                df = None
        norm = _normalize_bars(df)
        out[key] = norm
    return out


def pulse_status(symbol: str) -> Dict[str, int]:
    """Compute gate status for the given symbol and cache briefly in Redis.

    Returns a dict of 0/1 flags: context, liquidity, structure, imbalance, risk, confluence.
    """
    # Demo override (for presentations/testing)
    try:
        r_demo = _redis_client()
        if r_demo is not None:
            raw = r_demo.get(f"pulse_status:{symbol}:demo")
            if raw:
                obj = json.loads(raw)
                return {
                    k: (1 if float(v) > 0 else 0)
                    for k, v in obj.items()
                    if k in {"context", "liquidity", "structure", "imbalance", "risk", "confluence"}
                }
    except Exception:
        pass

    data = _load_minute_data(symbol)

    ctx = context_gate(data.get("H4"))  # or combine H4/H1
    liq = liquidity_gate(data.get("M15"))
    struct = structure_gate(data.get("M1"))
    imb = imbalance_gate(data.get("M1"))
    rsk = risk_gate(imb, struct, symbol)
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
