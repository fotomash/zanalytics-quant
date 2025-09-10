import json
import os
import time
from typing import Dict, Iterable, Optional

import redis

# Environment configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
ML_SIGNAL_STREAM = os.getenv("ML_SIGNAL_STREAM", "ml:signals")
ML_RISK_STREAM = os.getenv("ML_RISK_STREAM", "ml:risk")


class RedisMLBridge:
    """Bridge for publishing ML outputs to Redis streams."""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        signal_stream: str = ML_SIGNAL_STREAM,
        risk_stream: str = ML_RISK_STREAM,
    ) -> None:
        self.redis = redis_client or redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
        )
        self.signal_stream = signal_stream
        self.risk_stream = risk_stream

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
        self.redis.xadd(self.signal_stream, payload, maxlen=10000, approximate=True)
        # Publish risk portion to the risk stream
        self.redis.xadd(
            self.risk_stream,
            {"symbol": symbol, "risk": risk, "timestamp": payload["timestamp"]},
            maxlen=10000,
            approximate=True,
        )


def iter_model_outputs() -> Iterable[Dict[str, float]]:
    """Yield ML outputs from model pipelines.

    This placeholder yields mock data. Replace with real pipeline outputs.
    """
    symbols = os.getenv("ML_SYMBOLS", "AAPL,MSFT,GOOG").split(",")
    for sym in symbols:
        yield {
            "symbol": sym.strip(),
            "risk": 0.1,
            "alpha": 0.05,
            "confidence": 0.9,
        }


def main() -> None:
    bridge = RedisMLBridge()
    for signal in iter_model_outputs():
        bridge.publish(**signal)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
