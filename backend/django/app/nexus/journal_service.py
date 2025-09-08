from __future__ import annotations

import os
import requests
from typing import Optional, Dict, Any


DJANGO_INTERNAL_BASE = os.environ.get("DJANGO_INTERNAL_BASE", "http://django:8000").rstrip("/")


def journal_append(kind: str, text: str, *, meta: Optional[Dict[str, Any]] = None,
                   trade_id: Optional[int] = None, tags: Optional[list] = None) -> None:
    payload = {
        "kind": kind,
        "text": text,
        "meta": meta or {},
    }
    if trade_id is not None:
        payload["trade_id"] = int(trade_id)
    if tags:
        payload["tags"] = list(tags)
    try:
        url = f"{DJANGO_INTERNAL_BASE}/api/v1/journal/append"
        requests.post(url, json=payload, timeout=5)
    except Exception:
        # best-effort journaling; do not raise
        pass

