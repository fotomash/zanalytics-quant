"""Utilities for converting enriched pipeline output into Pulse dashboard payloads."""
from __future__ import annotations

from typing import Any, Dict, List
from schemas.payloads import UnifiedAnalysisPayloadV1


def build_harmonic_dashboard_payload(
    payload: UnifiedAnalysisPayloadV1, bars: List[Dict[str, Any]] | None
) -> Dict[str, Any]:
    """Convert unified analysis output to the dashboard harmonic schema.

    Parameters
    ----------
    payload:
        Enriched payload produced by the enrichment pipeline.
    bars:
        OHLC data used for deriving point timestamps. Each element should be a
        mapping containing at least ``time`` and price fields.
    """
    ohlc = bars or []

    patterns: List[Dict[str, Any]] = []
    for pattern in payload.harmonic.harmonic_patterns:
        transformed: Dict[str, Any] = {
            "pattern_type": pattern.get("pattern") or pattern.get("pattern_type"),
            "confidence": pattern.get("confidence", 0.0),
        }
        prz = pattern.get("prz", {})
        transformed["prz_low"] = pattern.get("prz_low", prz.get("low"))
        transformed["prz_high"] = pattern.get("prz_high", prz.get("high"))

        points = pattern.get("points", [])
        for idx, point in enumerate(points[:4], start=1):
            bar_index = point.get("index")
            time_val = None
            if isinstance(bar_index, int) and 0 <= bar_index < len(ohlc):
                time_val = ohlc[bar_index].get("time")
            transformed[f"point{idx}_time"] = time_val
            transformed[f"point{idx}_price"] = point.get("price")
        patterns.append(transformed)

    return {
        "symbol": payload.symbol,
        "timestamp": payload.timestamp.isoformat(),
        "ohlc": ohlc,
        "harmonic_patterns": patterns,
    }


__all__ = ["build_harmonic_dashboard_payload"]
