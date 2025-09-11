"""WebSocket helpers for Streamlit dashboards."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Callable, Dict

try:  # Optional import: websocket-client may not be installed everywhere
    import websocket  # type: ignore
except Exception:  # pragma: no cover - missing dependency
    websocket = None


def subscribe(topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
    """Subscribe to ``topic`` and invoke ``callback`` for each JSON message.

    The WebSocket endpoint is configured via ``LIVE_DATA_WS_URL`` and defaults
    to ``ws://localhost:8765``.
    """
    if websocket is None:  # pragma: no cover - defensive
        raise RuntimeError("websocket-client not installed")

    base_url = os.getenv("LIVE_DATA_WS_URL", "ws://localhost:8765")

    def _on_message(_: Any, message: str) -> None:
        try:
            payload = json.loads(message)
        except Exception:
            payload = {"raw": message}
        callback(payload)

    ws = websocket.WebSocketApp(
        f"{base_url}?topic={topic}",
        on_message=_on_message,
    )
    threading.Thread(target=ws.run_forever, daemon=True).start()
