import json
import time
from typing import Optional

import redis


class RedisMLBridge:
    """Bridge ML model output channels to structured Redis signals."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        input_channel: str = "model:outputs",
        output_channel: str = "signals",
        retry_interval: float = 1.0,
        redis_client: Optional[redis.Redis] = None,
    ) -> None:
        self.redis_url = redis_url
        self.input_channel = input_channel
        self.output_channel = output_channel
        self.retry_interval = retry_interval
        self.redis_client = redis_client
        self.pubsub = None

    def _connect(self) -> None:
        """Establish a Redis connection and subscribe to the input channel."""
        while True:
            try:
                if self.redis_client is None:
                    self.redis_client = redis.from_url(self.redis_url)
                self.redis_client.ping()
                self.pubsub = self.redis_client.pubsub()
                self.pubsub.subscribe(self.input_channel)
                break
            except redis.ConnectionError:
                # Reset client and retry after a delay
                self.redis_client = None
                time.sleep(self.retry_interval)

    def _structure(self, data: bytes) -> dict:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        payload = json.loads(data)
        return {"timestamp": time.time(), "payload": payload}

    def run_once(self) -> Optional[dict]:
        """Process a single message if available."""
        if self.pubsub is None:
            self._connect()
        try:
            message = self.pubsub.get_message(timeout=1.0)
            if message and message["type"] == "message":
                structured = self._structure(message["data"])
                self.redis_client.publish(
                    self.output_channel, json.dumps(structured)
                )
                return structured
        except (redis.ConnectionError, OSError):
            # Attempt to reconnect on failure
            self.pubsub = None
            self._connect()
        return None

    def run_forever(self) -> None:
        """Continuously process messages."""
        while True:
            self.run_once()

