from __future__ import annotations

"""Redis tick stream monitor that consults a local Ollama model.

This worker watches a Redis stream for tick data and triggers LLM
queries when market phases change or when confidence drops sharply.
The Ollama endpoint is expected to run locally and respond with a
simple text decision.
"""

import json
import os
import time
from typing import Dict

import requests
from redis import Redis
from services.common import get_logger


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM_PREFIX = os.getenv("DNS_PREFIX", "mcp2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "llama3")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", 1.0))

redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT)
last_phases: Dict[str, str] = {}

logger = get_logger(__name__)


def query_ollama(prompt: str) -> str:
    """Send ``prompt`` to the local Ollama endpoint and return the response."""

    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    return str(data.get("response", "")).strip()


def main() -> None:
    """Poll the Redis stream and react to phase changes or risk spikes."""

    stream_name = f"{STREAM_PREFIX}:ticks:"
    while True:
        streams = redis_client.xread({stream_name: ">"}, block=5000, count=10)
        for stream, msgs in streams:
            symbol = stream.split(":")[-1]
            for _, msg in msgs:
                tick = json.loads(msg[b"payload"])
                phase = tick["phase"]
                conf = tick["confidence"]
                price_change = tick.get("price_change_5m", 0.0)

                # Phase-change trigger
                if last_phases.get(symbol) != phase:
                    prompt = f"{symbol}: phase={phase}, confidence={conf:.2f}. Trade?"
                    decision = query_ollama(prompt)
                    logger.info("[Ollama] %s → %s → %s", symbol, phase, decision)
                    last_phases[symbol] = phase

                # Risk spike trigger
                if conf < 0.6 and price_change > 0.01:
                    prompt = (
                        f"{symbol}: risk alert. Confidence {conf:.2f}. Kill trade?"
                    )
                    decision = query_ollama(prompt)
                    logger.info("[Ollama] %s risk alert → %s", symbol, decision)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
