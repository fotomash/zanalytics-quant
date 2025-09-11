from __future__ import annotations

import os
import requests
from typing import Optional, Dict, Any


DJANGO_INTERNAL_BASE = os.environ.get("DJANGO_INTERNAL_BASE", "http://django:8000").rstrip("/")
DEFAULT_AGENT_ID = os.environ.get("AGENT_ID", "zanflow")


def journal_append(kind: str, text: str, *, meta: Optional[Dict[str, Any]] = None,
                   trade_id: Optional[int] = None, tags: Optional[list] = None,
                   agent_id: Optional[str] = None, timestamp: Optional[str] = None) -> None:
    payload: Dict[str, Any] = {
        "kind": kind,
        "text": text,
        "meta": meta or {},
    }
    if trade_id is not None:
        payload["trade_id"] = int(trade_id)
    if tags:
        payload["tags"] = list(tags)
    if agent_id or DEFAULT_AGENT_ID:
        payload["agent_id"] = agent_id or DEFAULT_AGENT_ID
    if timestamp:
        payload["timestamp"] = timestamp
    try:
        url = f"{DJANGO_INTERNAL_BASE}/api/v1/journal/append"
        requests.post(url, json=payload, timeout=5)
    except Exception:
        # best-effort journaling; do not raise
        pass


def journal_append_structured(kind: str, trade_id: int, text: str, *,
                              agent_id: Optional[str] = None, tags: Optional[list] = None,
                              meta: Optional[Dict[str, Any]] = None) -> None:
    """Helper that stamps ISO timestamp and ensures core fields are present.

    Use when building entries that align to the JournalEntry schema.
    """
    from datetime import datetime, timezone as _tz
    ts = datetime.now(tz=_tz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    journal_append(kind, text, meta=meta or {}, trade_id=trade_id, tags=tags or [], agent_id=agent_id, timestamp=ts)
