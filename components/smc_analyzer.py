"""Lightweight placeholder for SMC analysis used in tests."""

from __future__ import annotations
from typing import Any, Dict


class SMCAnalyzer:
    """Return a neutral Smart Money Concepts score."""

    def score(self, data: Any) -> Dict[str, Any]:
        return {"score": 50.0, "reasons": []}

