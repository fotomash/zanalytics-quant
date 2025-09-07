"""Policies loader with simple caching.

Reads a YAML file (path from POLICIES_PATH or defaults to app/policies.yaml) and returns a dict.
"""
from __future__ import annotations

import os
import time
from typing import Dict, Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

_CACHE: Dict[str, Any] = {"data": None, "exp": 0}


def _path() -> str:
    base = os.getenv("POLICIES_PATH")
    if base:
        return base
    # default relative to Django app
    here = os.path.dirname(__file__)
    return os.path.join(os.path.dirname(here), "policies.yaml")


def load_policies(ttl_seconds: int = 30) -> Dict[str, Any]:
    now = time.time()
    if _CACHE.get("data") and _CACHE.get("exp", 0) > now:
        return _CACHE["data"]
    path = _path()
    data: Dict[str, Any] = {}
    try:
        if yaml and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    _CACHE["data"] = data
    _CACHE["exp"] = now + ttl_seconds
    return data

