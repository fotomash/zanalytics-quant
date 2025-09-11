import os
import json
from datetime import datetime, timezone

try:
    from confluent_kafka import Consumer  # type: ignore
except Exception:  # pragma: no cover
    Consumer = None  # type: ignore

try:
    import psycopg2
    from psycopg2.extras import Json
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore
    Json = None  # type: ignore

BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
TOPIC = os.getenv("TOPIC", "enriched-analysis-payloads")
GROUP = os.getenv("KAFKA_GROUP", "enriched-persistence")
PG_DSN = os.getenv(
    "PG_DSN", "postgresql://postgres:timescale@timescaledb:5432/postgres"
)


def parse_ts(value: object) -> datetime:
    """Convert various timestamp representations to datetime."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:  # pragma: no cover - best effort
            pass
    return datetime.now(timezone.utc)


def main() -> None:
    if Consumer is None or psycopg2 is None:
        print("Missing dependencies for consumer; exiting")
        return

    c = Consumer(
        {
            "bootstrap.servers": BROKERS,
            "group.id": GROUP,
            "auto.offset.reset": "latest",
        }
    )
    c.subscribe([TOPIC])

    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    try:
        while True:
            msg = c.poll(1.0)
            if msg is None or msg.error():
                continue
            try:
                payload = json.loads(msg.value())
            except Exception:
                continue
            ts_raw = payload.get("timestamp") or payload.get("ts")
            ts = parse_ts(ts_raw)
            symbol = payload.get("symbol")
            try:
                cur.execute(
                    "INSERT INTO enriched_data (ts, symbol, payload) VALUES (%s, %s, %s)",
                    (ts, symbol, Json(payload)),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                continue
    finally:
        try:
            c.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
