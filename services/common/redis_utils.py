"""Redis helper utilities for services."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import redis

# Default TTL for behavioral scores (in seconds)
BEHAVIORAL_SCORE_TTL = int(os.getenv("BEHAVIORAL_SCORE_TTL", "3600"))


def set_behavioral_score(r: redis.Redis, trader_id: str, payload: Dict[str, Any]) -> None:
    """Store behavioral score payload for a trader with a TTL.

    Parameters
    ----------
    r:
        Redis client instance.
    trader_id:
        Identifier of the trader.
    payload:
        Behavioral metrics or score payload to store. Will be JSON encoded.
    """
    key = f"behavioral_metrics:{trader_id}"
    r.setex(key, BEHAVIORAL_SCORE_TTL, json.dumps(payload))
