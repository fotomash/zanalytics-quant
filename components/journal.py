"""Signal journal utilities.

The journal records signal evaluations and trade decisions to ``JSONL`` files
so that trading behaviour can be reviewed later.  Each entry is written as a
single JSON object per line allowing easy post-processing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any


@dataclass
class JournalEvent:
    ts: str = field(default_factory=lambda: datetime.now().isoformat())
    symbol: str = "UNKNOWN"
    score: float = 0.0
    grade: str = "Low"
    reasons: List[str] = field(default_factory=list)
    risk_status: str = "allowed"
    sl: float = 0.0  # stop loss
    tp: float = 0.0  # take profit
    decision: str = "accepted"
    outcome: str = ""
    rr_realized: float = 0.0
    violations: List[str] = field(default_factory=list)
    notes: str = ""


class Journal:
    """Accountability layer for recording signals and outcomes."""

    def __init__(self, path: str = "data/journal") -> None:
        self.base_path = Path(path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: Dict[str, Any]) -> None:
        record = JournalEvent(**event)
        fname = self.base_path / f"{date.today()}.jsonl"
        with fname.open("a") as fh:
            fh.write(json.dumps(asdict(record)) + "\n")

    def generate_weekly_report(self, output_path: str = "reports") -> Dict[str, Any]:
        """Create a rudimentary weekly report.

        The implementation is intentionally simple; full analytics would require
        Pandas or similar but is outside the scope of this foundation step.
        """

        out_dir = Path(output_path)
        out_dir.mkdir(exist_ok=True)
        report = {"week": date.today().isocalendar()[1], "avg_rr": 0, "outcomes": []}
        with (out_dir / f"week{report['week']}.json").open("w") as fh:
            json.dump(report, fh)
        return report
