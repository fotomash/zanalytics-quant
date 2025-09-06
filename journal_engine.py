"""Minimal journaling facility used by :mod:`pulse_kernel` tests.

The real project contains a richer journaling subsystem.  For the purposes of
testing, we only need a class with a ``log`` method accepting the standard
arguments used in the kernel.
"""

from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd

journal_events: List[Dict[str, Any]] = []


class JournalEngine:
    """No-op journal logger used in tests."""

    def __init__(self, journal_dir: str | None = None) -> None:
        self.journal_dir = journal_dir

    def log(self, ts: Any, symbol: str, score: Dict[str, Any], decision: Dict[str, Any]) -> None:
        journal_events.append({"ts": ts, "symbol": symbol, "score": score, "decision": decision})
        return None


def log_event(event: Dict[str, Any]) -> None:
    """Record an arbitrary journal event."""
    journal_events.append(event)


def check_tick_gaps(symbol: str, df: pd.DataFrame) -> None:
    """Detect gaps greater than 60s in tick data and log events."""
    if df.empty or "timestamp" not in df:
        return
    df = df.sort_values("timestamp")
    df["gap"] = df["timestamp"].diff().dt.total_seconds()
    gaps = df[df["gap"] > 60]
    for _, row in gaps.iterrows():
        log_event({
            "event": "data_gap",
            "symbol": symbol,
            "timestamp": row["timestamp"],
            "gap_seconds": row["gap"],
            "severity": "high" if row["gap"] > 300 else "medium",
        })

