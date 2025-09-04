"""Central orchestrator for Zanalytics Pulse.

The :class:`PulseKernel` glues together the scoring, risk and
journal components.  It receives market data, computes a
confluence score, checks behavioural risk limits and records the
outcome for later review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, Any

import pandas as pd

from confluence_scorer import ConfluenceScorer
from risk_enforcer import RiskEnforcer


@dataclass
class JournalEngine:
    """Tiny JSON based journal for process logging."""

    path: Path = Path("pulse_journal.json")

    def log(self, entry: Dict[str, Any]) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text())
        else:
            data = []
        data.append(entry)
        self.path.write_text(json.dumps(data, indent=2))


@dataclass
class PulseKernel:
    scorer: ConfluenceScorer = field(default_factory=ConfluenceScorer)
    risk: RiskEnforcer = field(default_factory=RiskEnforcer)
    journal: JournalEngine = field(default_factory=JournalEngine)

    def process(self, df: pd.DataFrame, trade: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Process new market data and optional trade information."""
        score = self.scorer.score(df)
        allowed, risk_info = self.risk.evaluate(trade)
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "score": score,
            "risk": risk_info,
            "allowed": allowed,
            "trade": trade,
        }
        self.journal.log(entry)
        return {"score": score, "risk": risk_info, "allowed": allowed}


def healthcheck() -> Dict[str, str]:
    """Lightweight health endpoint used by the API."""
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
