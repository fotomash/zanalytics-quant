from celery import shared_task
import logging

from app.utils.api.data import fetch_ticks, fetch_bars
from app.utils.constants import MT5Timeframe
from .models import Tick, Bar

logger = logging.getLogger(__name__)


@shared_task(name="nexus.tasks.update_tick_data")
def update_tick_data(symbol: str, limit: int = 100):
    """Fetch recent ticks and store them in the database."""
    df = fetch_ticks(symbol, limit)
    if df is None or df.empty:
        return
    for _, row in df.iterrows():
        Tick.objects.update_or_create(
            symbol=symbol,
            time=row["time"],
            defaults={
                "bid": row.get("bid"),
                "ask": row.get("ask"),
                "last": row.get("last"),
                "volume": row.get("volume"),
            },
        )


@shared_task(name="nexus.tasks.update_bar_data")
def update_bar_data(symbol: str, timeframe: str, limit: int = 100):
    """Fetch bar data and store them in the database."""
    tf = MT5Timeframe(timeframe)
    df = fetch_bars(symbol, tf, limit)
    if df is None or df.empty:
        return
    for _, row in df.iterrows():
        Bar.objects.update_or_create(
            symbol=symbol,
            timeframe=timeframe,
            time=row["time"],
            defaults={
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "tick_volume": row["tick_volume"],
                "spread": row["spread"],
                "real_volume": row["real_volume"],
            },
        )

