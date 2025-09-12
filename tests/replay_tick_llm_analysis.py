"""Replay historical ticks through EchoNudge and Whisperer paths.

This script loads a small subset of historical tick data and routes each
entry through both the local ``EchoNudge`` path and the remote ``Whisperer``
service.  For every tick it records:

* response latency for each path
* rough token usage (prompt + response word count)
* whether the two paths produced diverging decisions

Results are printed as a simple summary table to help with threshold tuning
and prompt refinement.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Callable, Dict, Tuple

try:  # Import LLM helpers; fall back to no-op stubs if unavailable
    from services.mcp2.llm_config import call_local_echo, call_whisperer
except Exception:  # pragma: no cover - import guard
    def call_local_echo(prompt: str) -> str:  # type: ignore
        return f"echo: {prompt}"

    def call_whisperer(prompt: str) -> str:  # type: ignore
        return f"whisperer: {prompt}"

DATA_PATH = Path(__file__).parent / "tick_samples" / "historical_ticks.json"


def _load_ticks(path: Path) -> list[Dict[str, float]]:
    return json.loads(path.read_text())


def _build_prompt(tick: Dict[str, float]) -> str:
    return (
        f"Quick nudge for {tick['phase']}, confidence "
        f"{tick['confidence']:.2f}: hold/sell/hedge?"
    )


def _measure(fn: Callable[[str], str], prompt: str) -> Tuple[str, float, int]:
    start = time.perf_counter()
    try:
        result = fn(prompt)
    except Exception as exc:  # pragma: no cover - network failure
        result = f"error: {exc}"
    latency = time.perf_counter() - start
    tokens = len(prompt.split()) + len(result.split())
    return result, latency, tokens


def main() -> None:
    ticks = _load_ticks(DATA_PATH)
    rows = []
    for tick in ticks:
        prompt = _build_prompt(tick)
        echo_res, echo_lat, echo_tok = _measure(call_local_echo, prompt)
        whisper_res, whisper_lat, whisper_tok = _measure(call_whisperer, prompt)
        rows.append(
            {
                "id": tick.get("id"),
                "echo_latency": echo_lat,
                "whisper_latency": whisper_lat,
                "echo_tokens": echo_tok,
                "whisper_tokens": whisper_tok,
                "divergent": echo_res != whisper_res,
            }
        )

    echo_avg = statistics.mean(r["echo_latency"] for r in rows)
    whisper_avg = statistics.mean(r["whisper_latency"] for r in rows)
    echo_tokens = sum(r["echo_tokens"] for r in rows)
    whisper_tokens = sum(r["whisper_tokens"] for r in rows)
    divergence = sum(r["divergent"] for r in rows)

    print("Tick Replay Summary\n===================")
    print(f"Processed {len(rows)} ticks")
    print(
        f"Avg latency - EchoNudge: {echo_avg:.3f}s, "
        f"Whisperer: {whisper_avg:.3f}s"
    )
    print(
        f"Total tokens - EchoNudge: {echo_tokens}, "
        f"Whisperer: {whisper_tokens}"
    )
    print(f"Decision divergences: {divergence}")
    for r in rows:
        print(
            f"Tick {r['id']}: divergence={r['divergent']}, "
            f"echo_latency={r['echo_latency']:.3f}s, "
            f"whisper_latency={r['whisper_latency']:.3f}s"
        )


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
