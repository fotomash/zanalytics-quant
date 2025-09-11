import os
import json
from datetime import datetime, timezone
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest

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

payloads_written_to_db_total = Counter(
    "payloads_written_to_db_total", "Total payloads written to DB"
)

# global references used by the health endpoint
kafka_consumer = None
pg_conn = None


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


def check_kafka() -> bool:
    if kafka_consumer is None:
        return False
    try:
        kafka_consumer.list_topics(timeout=5)
        return True
    except Exception:  # pragma: no cover - best effort
        return False


def check_pg() -> bool:
    if pg_conn is None:
        return False
    try:
        with pg_conn.cursor() as cur:  # type: ignore[arg-type]
            cur.execute("SELECT 1")
        return True
    except Exception:  # pragma: no cover - best effort
        return False


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # pragma: no cover - simple I/O
        if self.path == "/health":
            status = 200 if check_kafka() and check_pg() else 500
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b"ok" if status == 200 else b"unhealthy")
        elif self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(404)
            self.end_headers()


def run_http_server() -> None:
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    server.serve_forever()


def _write_batch(cur, batch: list[dict]) -> None:
    """Insert a batch of payloads using the given cursor."""
    params = []
    for payload in batch:
        ts_raw = payload.get("timestamp") or payload.get("ts")
        ts = parse_ts(ts_raw)
        symbol = payload.get("symbol")
        params.append((ts, symbol, Json(payload)))
    cur.executemany(
        "INSERT INTO enriched_data (ts, symbol, payload) VALUES (%s, %s, %s)",
        params,
    )
    payloads_written_to_db_total.inc(len(batch))


def replay_to_postgres(consumer, *, batch_size: int = 100) -> None:
    """Consume messages from ``consumer`` and persist them to Postgres."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required")
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    batch: list[dict] = []
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                break
            if msg.error():
                continue
            try:
                payload = json.loads(msg.value())
            except Exception:
                continue
            batch.append(payload)
            if len(batch) >= batch_size:
                _write_batch(cur, batch)
                conn.commit()
                batch.clear()
    finally:
        if batch:
            _write_batch(cur, batch)
            conn.commit()
        conn.close()


def main() -> None:
    if Consumer is None or psycopg2 is None:
        print("Missing dependencies for consumer; exiting")
        return

    global kafka_consumer, pg_conn

    kafka_consumer = Consumer(
        {
            "bootstrap.servers": BROKERS,
            "group.id": GROUP,
            "auto.offset.reset": "latest",
        }
    )
    kafka_consumer.subscribe([TOPIC])

    pg_conn = psycopg2.connect(PG_DSN)
    cur = pg_conn.cursor()

    threading.Thread(target=run_http_server, daemon=True).start()
    try:
        while True:
            msg = kafka_consumer.poll(1.0)
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
                pg_conn.commit()
                payloads_written_to_db_total.inc()
            except Exception:
                pg_conn.rollback()
                continue
    finally:
        try:
            kafka_consumer.close()
        except Exception:
            pass
        try:
            pg_conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
