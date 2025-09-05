"""Minimal journaling facility used by :mod:`pulse_kernel` tests.

The real project contains a richer journaling subsystem.  For the purposes of
testing, we only need a class with a ``log`` method accepting the standard
arguments used in the kernel.
"""

from __future__ import annotations
from typing import Any, Dict


class JournalEngine:
    """No-op journal logger used in tests."""

    def __init__(self, journal_dir: str | None = None) -> None:
        self.journal_dir = journal_dir

    def log(self, ts: Any, symbol: str, score: Dict[str, Any], decision: Dict[str, Any]) -> None:
        # In a full implementation we would persist to disk; here we simply
        # accept the call so that tests can run without side effects.
        return None

