from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import numpy as np
import os
import time
try:  # optional journal sink
    from .journal.kafka_journal import KafkaJournalEngine  # type: ignore
except Exception:
    KafkaJournalEngine = None  # type: ignore

# Tunables (can be adjusted as needed)
ASIA_START_UTC = "00:00"
ASIA_END_UTC = "07:00"  # widened from 06:00 → 07:00
ATR_SWEEP_MULT = 0.75     # increased from 0.5 → 0.75


def context_gate(data: pd.DataFrame | None) -> Dict[str, Any]:
    """Higher-timeframe context evaluation (skeleton).

    Returns at least {"passed": bool}; add details as needed.
    """
    return {"passed": False, "bias": None, "poi": None}


def wyckoff_gate(data: pd.DataFrame | None) -> Dict[str, Any]:
    """Minimal Wyckoff gate stub.

    Intention: detect an accumulation/distribution context via a simple
    range + breakout heuristic. Returns {passed, phase, direction}.

    This is a placeholder and safe to call when data is missing.
    """
    out: Dict[str, Any] = {"passed": False, "phase": None, "direction": None}
    if data is None or not isinstance(data, pd.DataFrame) or data.empty:
        return out
    try:
        df = data.copy().sort_values('timestamp').reset_index(drop=True)
        # Use last N bars to define a range
        win = df.tail(60)
        hi = float(win['high'].max())
        lo = float(win['low'].min())
        rng = hi - lo
        if rng <= 0:
            return out
        last = win.iloc[-1]
        # Break above range → distribution potential (bearish soon)
        # Break below range → accumulation potential (bullish soon)
        if float(last['close']) > hi:
            out.update(passed=True, phase='distribution?', direction='bearish?')
        elif float(last['close']) < lo:
            out.update(passed=True, phase='accumulation?', direction='bullish?')
    except Exception:
        return out
    return out


def liquidity_gate(data: pd.DataFrame | None, *, asia_start: str = ASIA_START_UTC,
                   asia_end: str = ASIA_END_UTC, atr_mult: float = ATR_SWEEP_MULT) -> Dict[str, Any]:
    """M15 liquidity sweep with snap-back confirmation.

    Implements two simple patterns:
    - Asian sweep: wick pierces Asian session (00:00–06:00 UTC) high/low by ≥0.5×ATR(14),
      then closes back inside the range within 3 bars.
    - Swing sweep (fallback): wick pierces last pivot high/low by ≥0.5×ATR, with snap-back.

    Returns dict with keys: passed, sweep_confirmed, sweep_type, direction, sweep_price, snapback_ts
    """
    out = {
        "passed": False,
        "sweep_confirmed": False,
        "sweep_type": None,
        "direction": None,  # bullish if low swept, bearish if high swept
        "sweep_price": None,
        "snapback_ts": None,
    }
    if data is None or not isinstance(data, pd.DataFrame) or data.empty:
        return out
    df = data.copy()
    if 'timestamp' not in df.columns:
        return out
    df = df.sort_values('timestamp').reset_index(drop=True)
    # Compute ATR(14) approximation on M15
    try:
        tr = (df['high'] - df['low']).abs()
        atr = tr.rolling(14, min_periods=14).mean()
        df['atr'] = atr
    except Exception:
        df['atr'] = (df['high'] - df['low']).abs().rolling(14, min_periods=14).mean()

    # Asian session window (UTC, configurable) for most recent session present
    try:
        df['ts'] = pd.to_datetime(df['timestamp'], utc=True)
        # Determine most recent session date present
        last_day = df['ts'].iloc[-1].date()
        session_start = pd.Timestamp.combine(last_day, pd.Timestamp(asia_start).time(), tz='UTC')
        session_end = pd.Timestamp.combine(last_day, pd.Timestamp(asia_end).time(), tz='UTC')
        asian = df[(df['ts'] >= session_start) & (df['ts'] <= session_end)]
        if asian.empty:
            # fallback to previous day
            prev_day = df['ts'].iloc[-1].normalize() - pd.Timedelta(days=1)
            session_start = prev_day
            # derive hours from configured window length
            _start = pd.Timestamp(asia_start)
            _end = pd.Timestamp(asia_end)
            hours = int((_end - _start).total_seconds() // 3600) or 6
            session_end = prev_day + pd.Timedelta(hours=hours)
        asian = df[(df['ts'] >= session_start) & (df['ts'] <= session_end)]
        if not asian.empty:
            asia_high = float(asian['high'].max())
            asia_low = float(asian['low'].min())
            # Look ahead after session for sweeps
            post = df[df['ts'] > session_end]
            if not post.empty:
                # Use last available ATR
                atr_last = float(df['atr'].iloc[-1] or 0)
                thresh = float(atr_mult) * atr_last if atr_last > 0 else 0.0
                # Check sweep of high
                for i in range(len(post)):
                    row = post.iloc[i]
                    # High sweep
                    if float(row['high']) > asia_high + thresh:
                        # snap-back within next 3 bars: close back inside the Asia range
                        nxt = post.iloc[i:i+4]
                        sb = nxt[nxt['close'] <= asia_high]
                        if not sb.empty:
                            out.update(
                                passed=True,
                                sweep_confirmed=True,
                                sweep_type='asian',
                                direction='bearish',
                                sweep_price=float(row['high']),
                                snapback_ts=str(sb.iloc[0]['timestamp'])
                            )
                            return out
                    # Low sweep
                    if float(row['low']) < asia_low - thresh:
                        nxt = post.iloc[i:i+4]
                        sb = nxt[nxt['close'] >= asia_low]
                        if not sb.empty:
                            out.update(
                                passed=True,
                                sweep_confirmed=True,
                                sweep_type='asian',
                                direction='bullish',
                                sweep_price=float(row['low']),
                                snapback_ts=str(sb.iloc[0]['timestamp'])
                            )
                            return out
    except Exception:
        pass

    # Fallback: swing sweep using recent pivots and ATR threshold
    try:
        def pivots(df: pd.DataFrame, lookback: int = 4):
            highs, lows = [], []
            for i in range(lookback, len(df) - lookback):
                win = df.iloc[i - lookback : i + lookback + 1]
                mid = df.iloc[i]
                if mid['high'] == win['high'].max():
                    highs.append((i, float(mid['high'])))
                if mid['low'] == win['low'].min():
                    lows.append((i, float(mid['low'])))
            return highs, lows

        hi_piv, lo_piv = pivots(df, lookback=4)
        hi_piv = hi_piv[-10:]
        lo_piv = lo_piv[-10:]
        if hi_piv or lo_piv:
            atr_last = float(df['atr'].iloc[-1] or 0)
            thresh = float(atr_mult) * atr_last if atr_last > 0 else 0.0
            # Scan the last 50 bars for sweeps
            window = df.iloc[-50:].reset_index(drop=True)
            for i, row in window.iterrows():
                # High sweep
                if hi_piv and float(row['high']) > max(h for _, h in hi_piv) + thresh:
                    nxt = window.iloc[i:i+4]
                    sb = nxt[nxt['close'] <= max(h for _, h in hi_piv)]
                    if not sb.empty:
                        out.update(passed=True, sweep_confirmed=True, sweep_type='swing', direction='bearish', sweep_price=float(row['high']), snapback_ts=str(sb.iloc[0]['timestamp']))
                        return out
                # Low sweep
                if lo_piv and float(row['low']) < min(l for _, l in lo_piv) - thresh:
                    nxt = window.iloc[i:i+4]
                    sb = nxt[nxt['close'] >= min(l for _, l in lo_piv)]
                    if not sb.empty:
                        out.update(passed=True, sweep_confirmed=True, sweep_type='swing', direction='bullish', sweep_price=float(row['low']), snapback_ts=str(sb.iloc[0]['timestamp']))
                        return out
    except Exception:
        pass

    return out


def structure_gate(m1: pd.DataFrame, *, pivot_lookback: int = 20) -> dict:
    """
    Detects a bullish or bearish Change-of-Character (CHoCH) – and optional
    Break-of-Structure (BoS) – on the M1 chart.

    A gate PASS = a valid CHoCH printed on an impulse candle whose volume
    is >= 1.5 × the median of the last 30 bars.

    Returns
    -------
    dict
        {
            "passed": bool,
            "direction": "bullish" | "bearish" | None,
            "choch_price": float | None,
            "bos_price":   float | None,
            "impulse_volume": float | None,
            "median_volume":  float | None
        }
    """
    out = dict(
        passed=False,
        direction=None,
        choch_price=None,
        bos_price=None,
        impulse_volume=None,
        median_volume=None,
    )

    # Sanity checks
    if m1 is None or m1.empty or len(m1) < 50:
        return out

    # Ensure newest row is last
    m1 = m1.sort_values("timestamp").reset_index(drop=True)

    # Swing-point detection (pivot highs/lows)
    def pivots(df: pd.DataFrame, lookback: int = 3):
        highs, lows = [], []
        for i in range(lookback, len(df) - lookback):
            window = df.iloc[i - lookback : i + lookback + 1]
            mid = df.iloc[i]
            if mid["high"] == window["high"].max():
                highs.append((i, mid["high"]))
            if mid["low"] == window["low"].min():
                lows.append((i, mid["low"]))
        return highs, lows

    hi_pivots, lo_pivots = pivots(m1, lookback=3)

    if not hi_pivots or not lo_pivots:
        return out

    # Keep only last few pivots
    hi_pivots = hi_pivots[-pivot_lookback:]
    lo_pivots = lo_pivots[-pivot_lookback:]

    last_hi_idx, last_hi = hi_pivots[-1]
    last_lo_idx, last_lo = lo_pivots[-1]

    # Last close / volume
    close_now = float(m1.iloc[-1]["close"])
    vol_now   = float(m1.iloc[-1]["volume"])
    vol_med   = float(m1["volume"].tail(30).median())

    out["impulse_volume"] = vol_now
    out["median_volume"]  = vol_med

    # Bullish CHoCH: prior downtrend (lower highs & lows) AND close > last pivot high with impulse volume
    if (
        close_now > last_hi
        and len(hi_pivots) >= 3
        and all(h1 > h2 for (_, h1), (_, h2) in zip(hi_pivots[-3:-1], hi_pivots[-2:]))
        and len(lo_pivots) >= 3
        and all(l1 > l2 for (_, l1), (_, l2) in zip(lo_pivots[-3:-1], lo_pivots[-2:]))
        and vol_now >= 1.5 * vol_med
    ):
        out.update(
            passed=True,
            direction="bullish",
            choch_price=float(last_hi),
        )

    # Bearish CHoCH: prior uptrend AND close < last pivot low with impulse volume
    elif (
        close_now < last_lo
        and len(hi_pivots) >= 3
        and all(h1 < h2 for (_, h1), (_, h2) in zip(hi_pivots[-3:-1], hi_pivots[-2:]))
        and len(lo_pivots) >= 3
        and all(l1 < l2 for (_, l1), (_, l2) in zip(lo_pivots[-3:-1], lo_pivots[-2:]))
        and vol_now >= 1.5 * vol_med
    ):
        out.update(
            passed=True,
            direction="bearish",
            choch_price=float(last_lo),
        )

    # Optional BoS check: follow-through swing in same direction
    if out["passed"]:
        if out["direction"] == "bullish":
            next_highs = [h for i, h in hi_pivots if i > last_hi_idx]
            if next_highs and close_now > max(next_highs):
                out["bos_price"] = float(max(next_highs))
        else:
            next_lows = [l for i, l in lo_pivots if i > last_lo_idx]
            if next_lows and close_now < min(next_lows):
                out["bos_price"] = float(min(next_lows))

    return out


def imbalance_gate(data: pd.DataFrame | None) -> Dict[str, Any]:
    """FVG / LPS detection derived from the impulse (skeleton)."""
    return {"passed": False, "entry_zone": [None, None]}


def _pip_size_for(symbol: str | None, price: float | None) -> float:
    try:
        s = (symbol or "").upper()
        if "JPY" in s:
            return 0.01
        if any(k in s for k in ("XAU", "GOLD")):
            return 0.1
        if any(k in s for k in ("XAG", "SILVER")):
            return 0.01
        if any(k in s for k in ("US500", "SPX", "SPX500")):
            return 1.0
    except Exception:
        pass
    # Fallback: default FX pip
    return 0.0001


def risk_gate(imbalance: Dict[str, Any], structure: Dict[str, Any], symbol: str | None = None) -> Dict[str, Any]:
    """Risk anchoring to swing + laddered TP.

    - Stop: last swing (approximated by CHoCH price) ± 3 pips in direction opposite to entry.
    - Entry: midpoint of imbalance entry_zone if available; else use CHoCH price.
    - Targets: 1R, 2R, 3R from entry in trade direction.
    """
    out = {"passed": False, "stop": None, "targets": [], "entry": None, "risk_r": None}
    try:
        if not isinstance(structure, dict) or not structure.get('passed'):
            return out
        choch_price = structure.get('choch_price')
        direction = structure.get('direction')  # 'bullish' or 'bearish'
        if choch_price is None or direction not in ('bullish', 'bearish'):
            return out
        # Entry from imbalance entry_zone midpoint when available
        entry = None
        if isinstance(imbalance, dict):
            ez = imbalance.get('entry_zone')
            if isinstance(ez, (list, tuple)) and len(ez) == 2 and all(isinstance(x, (int, float)) for x in ez):
                entry = (float(ez[0]) + float(ez[1])) / 2.0
        if entry is None:
            entry = float(choch_price)

        # Pip heuristic by symbol (fallback to FX default)
        pip = _pip_size_for(symbol, choch_price)
        pad = 3 * pip
        if direction == 'bullish':
            stop = float(choch_price) - pad
            risk = abs(entry - stop)
            targets = [entry + 1 * risk, entry + 2 * risk, entry + 3 * risk]
        else:
            stop = float(choch_price) + pad
            risk = abs(stop - entry)
            targets = [entry - 1 * risk, entry - 2 * risk, entry - 3 * risk]

        out.update(passed=True, stop=stop, targets=[float(t) for t in targets], entry=float(entry), risk_r=float(risk))
        # Journal the computed risk plan (feature-flagged; safe no-op)
        try:
            if KafkaJournalEngine is not None:
                je = KafkaJournalEngine()
                je.emit({
                    "ts": time.time(),
                    "stream": "pulse.risk_gate",
                    "symbol": str(symbol) if symbol is not None else None,
                    "frame": "1m",
                    "payload": {
                        "v": 1,
                        "direction": direction,
                        "entry": float(entry),
                        "stop": float(stop),
                        "targets": [float(t) for t in targets],
                        "risk_r": float(risk),
                    },
                })
        except Exception:
            pass
        return out
    except Exception:
        return out


def confluence_gate(data_bundle: Dict[str, pd.DataFrame] | None) -> Dict[str, Any]:
    """Optional enhancers (fib, volume, killzone, etc.) (skeleton)."""
    return {"passed": False, "confidence": 0.0}
