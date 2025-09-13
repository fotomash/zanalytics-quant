from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Sequence

from schemas import UnifiedAnalysisPayloadV1


def to_dashboard_payload(
    payload: UnifiedAnalysisPayloadV1, bars: Sequence[Dict[str, Any]] | None
) -> Dict[str, Any]:
    """Convert a unified analysis payload to the dashboard schema.

    Parameters
    ----------
    payload:
        The unified analysis payload produced by the enrichment pipeline.
    bars:
        Sequence of OHLC bars used during analysis. Each bar should contain
        ``time`` (or ``timestamp``), ``open``, ``high``, ``low`` and ``close``.

    Returns
    -------
    Dict[str, Any]
        Dictionary structured according to ``pulse_dashboard_config.yaml``.
    """

    bars = list(bars or [])
    ohlc = [
        {
            "time": b.get("time") or b.get("timestamp"),
            "open": b.get("open"),
            "high": b.get("high"),
            "low": b.get("low"),
            "close": b.get("close"),
        }
        for b in bars
    ]

    patterns = []
    for pat in payload.harmonic.harmonic_patterns:
        entry: Dict[str, Any] = {
            "pattern_type": pat.pattern,
            "confidence": pat.confidence,
        }
        for idx, point in enumerate(pat.points[:5], start=1):
            ts = None
            i = point.get("index")
            if i is not None:
                i = int(i)
                if 0 <= i < len(bars):
                    ts = bars[i].get("time") or bars[i].get("timestamp")
            entry[f"point{idx}_time"] = ts
            entry[f"point{idx}_price"] = point.get("price")
        entry["prz_low"] = pat.prz.get("min") or pat.prz.get("low")
        entry["prz_high"] = pat.prz.get("max") or pat.prz.get("high")
        patterns.append(entry)

    timestamp = payload.timestamp
    if isinstance(timestamp, datetime):
        timestamp_str = timestamp.isoformat()
    else:
        timestamp_str = str(timestamp)

    return {
        "symbol": payload.symbol,
        "timestamp": timestamp_str,
        "ohlc": ohlc,
        "harmonic_patterns": patterns,
    }


__all__ = ["to_dashboard_payload"]
