from celery import shared_task
import logging

from app.utils.api.data import fetch_ticks, fetch_bars
from app.utils.constants import MT5Timeframe
from .models import Tick, Bar
import os
import requests
from django.utils import timezone
from app.nexus.views import _redis_client

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


@shared_task(name="nexus.tasks.snapshot_sod_equity")
def snapshot_sod_equity():
    """Snapshot equity at 23:00 and persist as next-day SoD equity in Redis.

    - Reads equity from MT5 bridge `/account_info`
    - Stores under key: `sod_equity:YYYYMMDD` where date is (today + 1 day)
    """
    try:
        base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
        r = requests.get(f"{str(base).rstrip('/')}/account_info", timeout=2.0)
        if not r.ok:
            return False
        data = r.json() or {}
        if isinstance(data, list) and data:
            data = data[0]
        eq = float(data.get('equity') or data.get('Equity') or 0.0)
        if eq <= 0:
            return False
        # tomorrow's date as SoD key
        now = timezone.now()
        tomorrow = (now + timezone.timedelta(days=1)).strftime('%Y%m%d')
        cli = _redis_client()
        if cli is not None:
            cli.setex(f"sod_equity:{tomorrow}", 7*24*3600, str(eq))
        return True
    except Exception as e:
        logger.warning(f"snapshot_sod_equity failed: {e}")
        return False


@shared_task(name="nexus.tasks.modify_position_task")
def modify_position_task(ticket: int, sl: float = None, tp: float = None):
    """Asynchronously modify SL/TP for a position via the bridge."""
    from bridge.mt5 import modify_position
    try:
        ok, data = modify_position(ticket, sl=sl, tp=tp)
        if not ok:
            logger.error(f"Failed to modify position {ticket}: {data}")
        return ok, data
    except Exception as e:
        logger.error(f"Exception in modify_position_task for ticket {ticket}: {e}")
        return False, str(e)
