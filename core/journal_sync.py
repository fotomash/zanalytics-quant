"""Utilities to synchronize MetaTrader5 trade history with the Pulse journal."""

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:  # pragma: no cover - MT5 optional in tests
    mt5 = None  # type: ignore

from datetime import datetime, timezone
from typing import Dict, List
import json
import logging
import os
import sqlite3

try:  # pragma: no cover - optional dependency
    import redis
except Exception:  # pragma: no cover - handled gracefully in write_journal_entry
    redis = None  # type: ignore

logger = logging.getLogger(__name__)


def detect_behavior_flags(deal: object) -> List[str]:
    """Placeholder for behavioral flag detection logic."""
    return []

def write_journal_entry(entry: Dict) -> None:
    """Persist a journal entry to the configured backend.

    The backend is selected via the ``JOURNAL_BACKEND`` environment variable and
    supports ``redis`` (default) or ``sqlite`` for lightweight testing.  Errors
    are logged but never raised to avoid interrupting the sync process.
    """

    backend = os.getenv("JOURNAL_BACKEND", "redis").lower()

    if backend == "redis":
        if redis is None:  # pragma: no cover - library missing
            logger.warning("Redis backend requested but redis package is unavailable")
            return
        url = os.getenv("JOURNAL_REDIS_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
        try:
            client = redis.from_url(url, decode_responses=True)
            client.xadd("pulse:journal", entry, maxlen=1000, approximate=True)
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to write journal entry to Redis: %s", exc)
    elif backend == "sqlite":
        db_path = os.getenv("JOURNAL_DB_PATH", "journal.db")
        try:
            conn = sqlite3.connect(db_path)
            with conn:  # ensures commit/rollback
                conn.execute("CREATE TABLE IF NOT EXISTS journal (data TEXT)")
                conn.execute("INSERT INTO journal (data) VALUES (?)", (json.dumps(entry),))
        except Exception as exc:  # pragma: no cover - file/IO errors
            logger.error("Failed to write journal entry to SQLite: %s", exc)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    else:
        logger.error("Unknown JOURNAL_BACKEND '%s' - entry dropped", backend)


def sync_to_pulse_journal() -> Dict[str, int | str]:
    """Sync today's trade history from MT5 into the journal system."""
    if mt5 is None or not mt5.initialize():
        return {"error": "MT5 not connected"}

    from_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    to_date = datetime.now(timezone.utc)

    deals = mt5.history_deals_get(from_date, to_date)
    if deals is None:
        return {"synced": 0}

    journal_entries: List[Dict] = []
    for deal in deals:
        entry = {
            "ticket": deal.ticket,
            "symbol": deal.symbol,
            "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
            "volume": deal.volume,
            "price": deal.price,
            "profit": deal.profit,
            "time": datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat(),
            "behavior_flags": detect_behavior_flags(deal),
        }
        journal_entries.append(entry)

    for entry in journal_entries:
        write_journal_entry(entry)

    return {"synced": len(journal_entries)}
