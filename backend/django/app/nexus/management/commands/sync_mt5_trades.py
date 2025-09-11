from __future__ import annotations

import os
import requests
from datetime import datetime, timezone
from typing import Any, Dict, List, DefaultDict
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from app.nexus.models import Trade


def _parse_ts(val: Any) -> datetime | None:
    try:
        # Prefer numeric epoch seconds
        return datetime.fromtimestamp(float(val), tz=timezone.utc)
    except Exception:
        pass
    try:
        # ISO 8601 fallback
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


def _market_type_for_symbol(symbol: str) -> str:
    sym = (symbol or "").upper()
    fx_bases = ("EUR", "USD", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF")
    if any(b in sym for b in fx_bases):
        return "FOREX"
    if sym.startswith("XAU") or sym.startswith("XAG"):
        return "OTHER"
    return "OTHER"


class Command(BaseCommand):
    help = "Sync closed MT5 deals into the Trade model (best-effort aggregation by position)."

    def add_arguments(self, parser):
        parser.add_argument("--date_from", dest="date_from", help="ISO date (YYYY-MM-DD)")
        parser.add_argument("--date_to", dest="date_to", help="ISO date (YYYY-MM-DD)")

    def handle(self, *args, **opts):
        base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
        url = f"{str(base).rstrip('/')}/history_deals_get"

        # Date window
        try:
            dfrom = opts.get("date_from")
            if dfrom:
                dt_from = datetime.fromisoformat(dfrom)
            else:
                # default: start of current month UTC
                now = datetime.now(timezone.utc)
                dt_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        except Exception:
            now = datetime.now(timezone.utc)
            dt_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        try:
            dto = opts.get("date_to")
            dt_to = datetime.fromisoformat(dto) if dto else datetime.now(timezone.utc)
        except Exception:
            dt_to = datetime.now(timezone.utc)

        params = {"from_date": dt_from.isoformat(), "to_date": dt_to.isoformat()}
        self.stdout.write(self.style.NOTICE(f"Fetching MT5 deals {params['from_date']} → {params['to_date']}"))
        try:
            resp = requests.get(url, params=params, timeout=8.0)
            data = resp.json() if resp.ok else []
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"MT5 bridge error: {e}"))
            return

        if not isinstance(data, list) or not data:
            self.stdout.write(self.style.WARNING("No deals returned by MT5 bridge."))
            return

        # Group by position id when available; else by ticket
        groups: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        for d in data:
            key = str(d.get("position") or d.get("ticket") or d.get("order") or "")
            if not key:
                continue
            groups[key].append(d)

        created = 0
        updated = 0
        with transaction.atomic():
            for pos_id, deals in groups.items():
                try:
                    deals_sorted = sorted(deals, key=lambda x: float(x.get("time") or 0))
                except Exception:
                    deals_sorted = deals

                sym = str((deals_sorted[0].get("symbol") if deals_sorted else "") or "").upper()
                ts_open = _parse_ts(deals_sorted[0].get("time") if deals_sorted else None)
                ts_close = _parse_ts(deals_sorted[-1].get("time") if deals_sorted else None)
                price_open = None
                price_close = None
                vol_sum = 0.0
                pnl_sum = 0.0
                commission_sum = 0.0
                buy_count = 0
                sell_count = 0
                for i, d in enumerate(deals_sorted):
                    try:
                        vol = float(d.get("volume") or 0.0)
                    except Exception:
                        vol = 0.0
                    vol_sum += vol
                    try:
                        pnl_sum += float(d.get("profit") or 0.0)
                    except Exception:
                        pass
                    try:
                        commission_sum += float(d.get("commission") or 0.0)
                    except Exception:
                        pass
                    typ = str(d.get("type") or "").upper()
                    if typ.endswith("BUY"):
                        buy_count += 1
                    elif typ.endswith("SELL"):
                        sell_count += 1
                    if i == 0:
                        try:
                            price_open = float(d.get("price") or d.get("price_open") or 0.0)
                        except Exception:
                            price_open = 0.0
                    if i == len(deals_sorted) - 1:
                        try:
                            price_close = float(d.get("price") or d.get("price_close") or 0.0)
                        except Exception:
                            price_close = 0.0

                if price_open is None:
                    price_open = 0.0
                if price_close is None:
                    price_close = 0.0

                trade_type = "BUY" if buy_count >= sell_count else "SELL"

                # Required numeric fields — best-effort estimates
                position_size_usd = abs(vol_sum * (price_open or 0.0))
                capital = position_size_usd
                leverage = 500.0
                liquidity_price = price_open or 0.0
                break_even_price = price_open or 0.0
                order_commission = commission_sum

                # Create or update by transaction_broker_id (use position id / ticket)
                defaults = {
                    "symbol": sym,
                    "entry_time": ts_open or ts_close or datetime.now(timezone.utc),
                    "entry_price": float(price_open or 0.0),
                    "type": trade_type,
                    "position_size_usd": float(position_size_usd or 0.0),
                    "capital": float(capital or 0.0),
                    "leverage": float(leverage),
                    "order_volume": float(vol_sum or 0.0),
                    "liquidity_price": float(liquidity_price),
                    "break_even_price": float(break_even_price),
                    "order_commission": float(order_commission or 0.0),
                    "close_time": ts_close,
                    "close_price": float(price_close or 0.0),
                    "pnl": float(pnl_sum),
                    "pnl_excluding_commission": float(pnl_sum - order_commission),
                    "max_drawdown": None,
                    "max_profit": None,
                    "closing_reason": "OTHER",
                    "strategy": "import_sync",
                    "broker": "MT5",
                    "market_type": _market_type_for_symbol(sym),
                    "timeframe": "1H",
                }

                obj, was_created = Trade.objects.update_or_create(
                    transaction_broker_id=str(pos_id), defaults=defaults
                )
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete: created={created}, updated={updated}, groups={len(groups)}"
            )
        )

