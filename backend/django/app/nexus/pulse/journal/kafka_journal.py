from __future__ import annotations

import os
import time
from typing import Optional, Dict, Any

try:
    # Optional dependency; when missing we operate as a no-op
    from confluent_kafka import Producer  # type: ignore
except Exception:  # pragma: no cover
    Producer = None  # type: ignore


class KafkaJournalEngine:
    """Feature-flagged Kafka journal sink (fail-closed, no-throw).

    Env/config:
      - USE_KAFKA_JOURNAL=false|true (default false)
      - KAFKA_BROKERS=kafka:9092
      - PULSE_JOURNAL_TOPIC=pulse.journal
    """

    def __init__(
        self,
        *,
        brokers: Optional[str] = None,
        topic: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.enabled = bool(
            enabled if enabled is not None else os.getenv("USE_KAFKA_JOURNAL", "false").lower() == "true"
        )
        self.brokers = brokers or os.getenv("KAFKA_BROKERS", "kafka:9092")
        self.topic = topic or os.getenv("PULSE_JOURNAL_TOPIC", "pulse.journal")
        self._producer = None
        if self.enabled and Producer is not None:  # type: ignore
            try:  # pragma: no cover - exercised in integration
                self._producer = Producer({"bootstrap.servers": self.brokers})
            except Exception:
                # disable on failure to init, but do not raise
                self.enabled = False

    def emit(self, event: Dict[str, Any]) -> None:
        """Emit a journal event (no-throw, best-effort)."""
        if not self.enabled or not self._producer:
            return
        try:  # pragma: no cover - exercised in integration
            import json
            payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
            self._producer.produce(self.topic, payload)
        except Exception:
            # Never throw into trading paths
            pass

    def flush(self, timeout_s: float = 2.0) -> None:
        if self._producer is None:
            return
        try:  # pragma: no cover
            self._producer.flush(timeout_s)
        except Exception:
            pass


def example_envelope(symbol: str, score_value: float) -> Dict[str, Any]:
    """Helper to build a sample envelope; not used in production paths."""
    return {
        "ts": time.time(),
        "stream": "pulse.score",
        "symbol": symbol,
        "frame": "1m",
        "payload": {"v": 1, "score": score_value},
        "trace_id": None,
    }

