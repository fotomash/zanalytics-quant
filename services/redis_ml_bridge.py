import json
import os
import time
from typing import Dict, Iterable, Optional

import redis

# Environment configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_VERSION = os.getenv("STREAM_VERSION", "1")
ML_SIGNAL_STREAM = os.getenv("ML_SIGNAL_STREAM", f"ml:signals:v{STREAM_VERSION}")
ML_RISK_STREAM = os.getenv("ML_RISK_STREAM", f"ml:risk:v{STREAM_VERSION}")
MODEL_OUTPUT_STREAM = os.getenv(
    "MODEL_OUTPUT_STREAM", f"ml:model_output:v{STREAM_VERSION}"
)
STREAM_BLOCK_MS = int(os.getenv("MODEL_STREAM_BLOCK_MS", "1000"))
STREAM_MAXLEN = int(os.getenv("ML_STREAM_MAXLEN", "10000"))


class RedisMLBridge:
    """Bridge for publishing ML outputs to Redis streams."""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        signal_stream: str = ML_SIGNAL_STREAM,
        risk_stream: str = ML_RISK_STREAM,
        maxlen: int = STREAM_MAXLEN,
    ) -> None:
        self.redis = redis_client or redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
        )
        self.signal_stream = signal_stream
        self.risk_stream = risk_stream
        self.maxlen = maxlen

    def publish(self, symbol: str, risk: float, alpha: float, confidence: float) -> None:
        """Publish a structured signal to Redis streams."""
        payload = {
            "symbol": symbol,
            "risk": risk,
            "alpha": alpha,
            "confidence": confidence,
            "timestamp": time.time(),
        }
        # Publish full payload to the signals stream
        self.redis.xadd(self.signal_stream, payload, maxlen=self.maxlen, approximate=True)
        # Publish risk portion to the risk stream
        self.redis.xadd(
            self.risk_stream,
            {"symbol": symbol, "risk": risk, "timestamp": payload["timestamp"]},
            maxlen=self.maxlen,
            approximate=True,
        )


def iter_model_outputs(
    redis_client: Optional[redis.Redis] = None,
    stream_name: str = MODEL_OUTPUT_STREAM,
    block_ms: int = STREAM_BLOCK_MS,
) -> Iterable[Dict[str, float]]:
    """Yield ML outputs from the model output stream.

    This generator reads messages from a Redis stream and yields structured
    dictionaries containing ``symbol``, ``risk``, ``alpha`` and ``confidence``
    values. It blocks for ``block_ms`` milliseconds waiting for new messages.
    """

    client = redis_client or redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
    )
    last_id = "$"
    while True:
        response = client.xread({stream_name: last_id}, block=block_ms, count=1)
        if not response:
            continue
        _, messages = response[0]
        for msg_id, fields in messages:
            last_id = msg_id
            try:
                yield {
                    "symbol": fields["symbol"],
                    "risk": float(fields["risk"]),
                    "alpha": float(fields["alpha"]),
                    "confidence": float(fields["confidence"]),
                }
            except KeyError:
                continue


def main() -> None:
    bridge = RedisMLBridge()
    for signal in iter_model_outputs(redis_client=bridge.redis):
        bridge.publish(**signal)


if __name__ == "__main__":
    main()
