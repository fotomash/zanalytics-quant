from __future__ import annotations

import json
from typing import Dict, Any, Optional
import os
import json
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
from .confluence_score_engine import compute_confluence_score
from .gates import KafkaJournalEngine as _KafkaJournalEngine
import time as _time


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


def _resolve_weights(weights: Optional[Dict[str, float]] = None, *, symbol: Optional[str] = None) -> Dict[str, float]:
    """Resolve confluence weights from overrides, env, or defaults."""
    if isinstance(weights, dict) and weights:
        return weights
    # 0) Try Redis-persisted weights
    try:
        r = _redis_client()
        if r is not None:
            # Prefer symbol-specific override
            raw = None
            if symbol:
                raw = r.get(f"pulse:conf_weights:{symbol}")
            if not raw:
                raw = r.get("pulse:conf_weights")
            if raw:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    w = obj.get("weights") or {}
                    if isinstance(w, dict) and w:
                        return {k: float(v) for k, v in w.items() if isinstance(v, (int, float))}
    except Exception:
        pass
    # Try env var JSON: PULSE_CONF_WEIGHTS='{"context":0.2,"liquidity":0.2,"structure":0.25,"imbalance":0.15,"risk":0.2}'
    try:
        raw = os.getenv('PULSE_CONF_WEIGHTS')
        if raw:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return {k: float(v) for k, v in obj.items() if isinstance(v, (int, float))}
    except Exception:
        pass
    # Fallback defaults (balanced)
    return {"context": 0.2, "liquidity": 0.2, "structure": 0.25, "imbalance": 0.15, "risk": 0.2}


def _resolve_threshold(*, symbol: Optional[str] = None, default: float = 0.6) -> float:
    # Symbol-specific in Redis, then global in Redis, then env, then default
    try:
        r = _redis_client()
        if r is not None:
            raw = None
            if symbol:
                raw = r.get(f"pulse:conf_weights:{symbol}")
            if not raw:
                raw = r.get("pulse:conf_weights")
            if raw:
                obj = json.loads(raw)
                thr = obj.get("threshold") if isinstance(obj, dict) else None
                if isinstance(thr, (int, float)):
                    return float(thr)
    except Exception:
        pass
    try:
        return float(os.getenv('PULSE_CONF_THRESHOLD', str(default)))
    except Exception:
        return float(default)


def pulse_status(symbol: str, *, weights: Optional[Dict[str, float]] = None, threshold: Optional[float] = None) -> Dict[str, int | float]:
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
    # Confluence score from gate results
    w = _resolve_weights(weights, symbol=symbol)
    thr = float(threshold) if isinstance(threshold, (int, float)) else _resolve_threshold(symbol=symbol, default=0.6)
    gates_for_score = {
        "context": ctx,
        "liquidity": liq,
        "structure": struct,
        "imbalance": imb,
        "risk": rsk,
    }
    score, details = compute_confluence_score(gates_for_score, w, threshold=thr)
    conf = {"passed": bool(details.get("score_passed")), "confidence": float(score)}

    status = {
        "context": int(bool(ctx.get("passed"))),
        "liquidity": int(bool(liq.get("passed"))),
        "structure": int(bool(struct.get("passed"))),
        "imbalance": int(bool(imb.get("passed"))),
        "risk": int(bool(rsk.get("passed"))),
        "confluence": int(bool(conf.get("passed"))),
        "confidence": round(float(score), 4),
    }

    # Cache to Redis with very short TTL
    r = _redis_client()
    try:
        if r is not None:
            key_sym = f"pulse_status:{symbol}"
            r.setex(key_sym, 5, json.dumps(status))
            # Also write a generic key for dashboards not passing symbol yet
            r.setex("pulse:status", 5, json.dumps(status))
            # Emit per-gate hit/miss events into a capped Redis list
            now_ts = _time.time()
            now_iso = None
            try:
                import datetime as _dt
                now_iso = _dt.datetime.utcfromtimestamp(now_ts).isoformat() + "Z"
            except Exception:
                now_iso = None
            for g in ("context", "liquidity", "structure", "imbalance", "risk"):
                try:
                    ev = {
                        "ts": now_ts,
                        "timestamp": now_iso,
                        "symbol": symbol,
                        "gate": g,
                        "passed": bool(status.get(g, 0)),
                        "score": float(status.get("confidence") or 0.0),
                    }
                    r.rpush("pulse:gate_hits", json.dumps(ev))
                except Exception:
                    pass
            try:
                r.ltrim("pulse:gate_hits", -300, -1)
            except Exception:
                pass
    except Exception:
        pass

    # Optional Kafka journal for gate events (best-effort)
    try:
        if _KafkaJournalEngine is not None:
            kj = _KafkaJournalEngine()
            if getattr(kj, "enabled", False):
                for g in ("context", "liquidity", "structure", "imbalance", "risk"):
                    try:
                        kj.emit({
                            "ts": _time.time(),
                            "stream": "pulse.gate-hits",
                            "symbol": symbol,
                            "frame": "1m",
                            "payload": {
                                "v": 1,
                                "gate": g,
                                "passed": bool(status.get(g, 0)),
                                "score": float(status.get("confidence") or 0.0),
                            },
                        })
                    except Exception:
                        pass
    except Exception:
        pass

    return status
