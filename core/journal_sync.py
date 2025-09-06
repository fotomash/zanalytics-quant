"""Utilities to synchronize MetaTrader5 trade history with the Pulse journal."""

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:  # pragma: no cover - MT5 optional in tests
    mt5 = None  # type: ignore

from datetime import datetime, timezone
from typing import Dict, List


def detect_behavior_flags(deal: object) -> List[str]:
    """Placeholder for behavioral flag detection logic."""
    return []


def write_journal_entry(entry: Dict) -> None:
    """Placeholder for writing a journal entry to storage."""
    # In production, this would persist to a database or message queue.
    pass


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
