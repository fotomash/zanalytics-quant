"""Streamlit dashboard with live data retrieval and caching."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import streamlit as st

try:  # Optional imports; modules may not be installed in all environments
    import redis  # type: ignore
except Exception:  # pragma: no cover - missing dependency
    redis = None

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover - missing dependency
    psycopg2 = None


@st.cache_data(ttl=30)
def get_live_data(symbol: str = "EURUSD") -> Dict[str, Any]:
    """Fetch the latest market data for ``symbol``.

    The backend is chosen via the ``LIVE_DATA_BACKEND`` environment variable
    (``redis`` or ``postgres``). The function gracefully falls back to a
    placeholder payload if anything goes wrong.
    """

    fallback = {"symbol": symbol, "bid": None, "ask": None}
    backend = os.getenv("LIVE_DATA_BACKEND", "redis").lower()

    try:
        if backend == "postgres":
            if psycopg2 is None:
                raise RuntimeError("psycopg2 not installed")
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT bid, ask FROM live_quotes WHERE symbol = %s ORDER BY ts DESC LIMIT 1",
                    (symbol,),
                )
                row = cur.fetchone()
            conn.close()
            if not row:
                return fallback
            bid, ask = row
            return {"symbol": symbol, "bid": bid, "ask": ask}

        # Default to Redis
        if redis is None:
            raise RuntimeError("redis not installed")
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
        )
        raw = client.get(f"live:{symbol}")
        if raw:
            data = json.loads(raw)
            data.setdefault("symbol", symbol)
            return data
        return fallback

    except Exception as exc:  # pragma: no cover - defensive
        st.warning(f"Live data unavailable: {exc}")
        return fallback


def main() -> None:
    """Simple demo page showing live data."""

    st.title("Enhanced Pulse Dashboard")
    symbol = st.text_input("Symbol", value="EURUSD")
    st.json(get_live_data(symbol))


if __name__ == "__main__":  # pragma: no cover
    main()
