import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class SessionJournal:
    """Simple JSON-backed journal for session actions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def append(self, action: str, decision: str, **meta: Any) -> None:
        entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "decision": decision,
        }
        entry.update(meta)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data.append(entry)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def flush(self) -> None:
        """Ensure journal contents are flushed to disk."""
        with self.path.open("r+") as fh:
            fh.flush()
            os.fsync(fh.fileno())
