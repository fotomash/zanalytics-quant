import json
import logging
from confluent_kafka import Producer

log = logging.getLogger(__name__)

class MT5KafkaProducer:
    """
    Thin wrapper around confluent_kafka.Producer that serialises a dict
    (the tick payload) as JSON and sends it to the configured topic.
    """
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "mt5.ticks",
        linger_ms: int = 5,
        batch_num_messages: int = 100,
    ):
        self.topic = topic
        self.producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "linger.ms": linger_ms,
                "batch.num.messages": batch_num_messages,
                "acks": "all",
                "enable.idempotence": True,
            }
        )

    def _delivery_report(self, err, msg):
        """Called on every message delivery."""
        if err is not None:
            log.error(f"Failed to deliver tick {msg.key()}: {err}")
        else:
            log.debug(
                f"Tick delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}"
            )

    def send_tick(self, tick: dict):
        """Publish a single tick. ``tick`` must be JSON-serialisable."""
        try:
            payload = json.dumps(tick).encode("utf-8")
            self.producer.produce(
                topic=self.topic,
                value=payload,
                callback=self._delivery_report,
            )
            self.producer.poll(0)
        except Exception as exc:
            log.exception(f"Exception while sending tick to Kafka: {exc}")

    def flush(self, timeout: float = 10.0):
        """Block until all queued messages are delivered."""
        self.producer.flush(timeout)

    def close(self) -> None:
        """Close the underlying Kafka producer."""
        try:
            self.producer.close()
        except Exception:
            # Closing the producer is best-effort; ignore failures
            pass
