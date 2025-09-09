from rest_framework import viewsets, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.utils import timezone
import time
from .models import Trade, TradeClosePricesMutation, Tick, Bar, PsychologicalState, JournalEntry
from .serializers import (
    TradeSerializer,
    TradeClosePricesMutationSerializer,
    TickSerializer,
    BarSerializer,
    PsychologicalStateSerializer,
    JournalEntrySerializer,
    MirrorStateSerializer,
    DisciplineSummarySerializer,
)
from .filters import TradeFilter, TickFilter, BarFilter

from app.utils.api.order import send_market_order, modify_sl_tp as modify_sl_tp_position
from .orders_service import modify_sl_tp as modify_sl_tp_ticket
from app.utils.arithmetics import convert_lots_to_usd, calculate_commission, get_price_at_pnl
from app.utils.policies import load_policies
import os
import requests
import json
import statistics
import json as _json
import math
from zoneinfo import ZoneInfo
from datetime import timedelta

try:
    import redis as redis_lib  # optional
except Exception:
    redis_lib = None


class PingView(views.APIView):
    """Simple health check endpoint."""

    def get(self, request):
        return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Lightweight health endpoint used by monitors.

    Returns HTTP 200 with a small JSON payload without requiring auth.
    """
    return Response({"status": "ok"})


def _trading_day_start_utc(now=None) -> "timezone.datetime":
    """Return the start of the current trading day in UTC.

    Trading day anchor is configurable via env:
      - TRADING_DAY_TZ (default Europe/London)
      - TRADING_DAY_ANCHOR_HOUR (default 23)  # 23:00 local time (11pm UK)
    If current local time is before anchor, roll back to previous day.
    """
    from django.utils import timezone
    tz_name = os.getenv("TRADING_DAY_TZ", "Europe/London")
    anchor_hour = int(os.getenv("TRADING_DAY_ANCHOR_HOUR", "23"))
    now = now or timezone.now()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    local_now = now.astimezone(tz)
    anchor_local = local_now.replace(hour=anchor_hour, minute=0, second=0, microsecond=0)
    if local_now < anchor_local:
        anchor_local = anchor_local - timedelta(days=1)
    return anchor_local.astimezone(ZoneInfo("UTC"))

# Session window helper (explicit bounds and stable session key)
SESSION_TZ = os.getenv("PULSE_SESSION_TZ", "Europe/London")
SESSION_CUTOFF_HOUR = int(os.getenv("PULSE_SESSION_CUTOFF_HOUR", "23"))

def session_bounds(now=None, cutoff_hour: int = SESSION_CUTOFF_HOUR, tz_name: str = SESSION_TZ):
    """Return (start_utc, end_utc, session_key) for the current trading session.

    Session runs from cutoff_hour local to cutoff_hour next day.
    session_key = date (YYYYMMDD) of the session END in local tz.
    """
    from django.utils import timezone
    now = now or timezone.now()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    local = now.astimezone(tz)
    cut = local.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
    if local >= cut:
        start_local = cut
        end_local = cut + timedelta(days=1)
        session_key = end_local.strftime("%Y%m%d")
    else:
        start_local = cut - timedelta(days=1)
        end_local = cut
        session_key = end_local.strftime("%Y%m%d")
    return start_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(ZoneInfo("UTC")), session_key

class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    filterset_class = TradeFilter
    ordering_fields = ['entry_time', 'close_time', 'pnl', 'symbol']
    ordering = ['-entry_time']  # default ordering

    def get_queryset(self):
        # Ensure we prefetch the related mutations to avoid N+1 queries
        return Trade.objects.prefetch_related('close_prices_mutations').all()

class SendMarketOrderView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required_fields = ['symbol', 'volume', 'order_type']
        for field in required_fields:
            if field not in data:
                return Response({'error': f'Missing field: {field}'}, status=status.HTTP_400_BAD_REQUEST)
        
        symbol = data.get('symbol')
        volume = data.get('volume')
        order_type = data.get('order_type')
        sl = data.get('sl', 0.0)
        tp = data.get('tp', 0.0)
        deviation = data.get('deviation', 20)
        comment = data.get('comment', '')
        magic = data.get('magic', 0)
        type_filling = data.get('type_filling', '2')

        order_response = send_market_order(
            symbol=symbol,
            volume=volume,
            order_type=order_type,
            sl=sl,
            tp=tp,
            deviation=deviation,
            comment=comment,
            magic=magic,
            type_filling=type_filling
        )

        if not order_response:
            return Response({'error': 'Failed to send market order.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            trade = Trade.objects.get(symbol=symbol, entry_price=order_response['price'])
            trade_serializer = TradeSerializer(trade)
            
            mutations = trade.close_prices_mutations.all()
            mutations_serializer = TradeClosePricesMutationSerializer(mutations, many=True)

            return Response({
                'trade': trade_serializer.data,
                'mutations': mutations_serializer.data
            }, status=status.HTTP_201_CREATED)
        except Trade.DoesNotExist:
            return Response({'error': 'Trade created but not found in database.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModifySLTPView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        ticket = data.get('ticket')
        if ticket is None:
            return Response({'error': 'Missing field: ticket'}, status=status.HTTP_400_BAD_REQUEST)

        sl = data.get('sl') or data.get('stop_loss')
        tp = data.get('tp') or data.get('take_profit')
        if sl is None and tp is None:
            return Response({'error': 'Provide sl and/or tp'}, status=status.HTTP_400_BAD_REQUEST)

        ok, modify_response = modify_sl_tp_ticket(int(ticket), sl=sl, tp=tp)
        if not ok:
            return Response({'error': 'Failed to modify SL/TP.', 'detail': modify_response},
                            status=status.HTTP_400_BAD_REQUEST)

        trade_id = data.get('id')
        if trade_id is not None:
            try:
                mutation = TradeClosePricesMutation.objects.filter(trade__id=trade_id).latest('mutation_time')
                mutation_serializer = TradeClosePricesMutationSerializer(mutation)
                return Response({'mutation': mutation_serializer.data}, status=status.HTTP_201_CREATED)
            except TradeClosePricesMutation.DoesNotExist:
                return Response({'error': 'Mutation created but not found in database.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'ok': True, 'result': modify_response}, status=status.HTTP_200_OK)


class TickViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tick.objects.all()
    serializer_class = TickSerializer
    filterset_class = TickFilter
    ordering = ["-time"]


class BarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bar.objects.all()
    serializer_class = BarSerializer
    filterset_class = BarFilter
    ordering = ["-time"]


class SymbolListView(views.APIView):
    """Return a list of available symbols."""

    def get(self, request):
        symbols = (
            Bar.objects.values_list("symbol", flat=True)
            .distinct()
            .order_by("symbol")
        )
        if not symbols:
            symbols = (
                Trade.objects.values_list("symbol", flat=True)
                .distinct()
                .order_by("symbol")
            )
        return Response({"symbols": list(symbols)})


class TimeframeListView(views.APIView):
    """Return a list of available timeframes."""

    def get(self, request):
        timeframes = (
            Bar.objects.values_list("timeframe", flat=True)
            .distinct()
            .order_by("timeframe")
        )
        if not timeframes:
            timeframes = (
                Trade.objects.values_list("timeframe", flat=True)
                .distinct()
                .order_by("timeframe")
            )
        return Response({"timeframes": list(timeframes)})


class DashboardDataView(views.APIView):
    """Aggregate dashboard payload for Streamlit.

    Returns:
      - psychological_state: latest PsychologicalState (if any)
      - confluence_score: placeholder for now (hook to pulse_api)
      - risk_metrics: simple daily PnL, trades_today
      - opportunities: [] (placeholder)
      - recent_journal: recent JournalEntry items
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Latest psychological state
        latest_psych = PsychologicalState.objects.order_by('-timestamp').first()
        psych_payload = PsychologicalStateSerializer(latest_psych).data if latest_psych else None

        # Risk metrics (basic): PnL today and trades today
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        sod = now.replace(hour=0, minute=0, second=0, microsecond=0)
        trades_today = Trade.objects.filter(entry_time__gte=sod)
        closed_today = trades_today.exclude(close_time__isnull=True)
        pnl_today = sum([t.pnl or 0 for t in closed_today])

        risk_metrics = {
            "trades_today": trades_today.count(),
            "pnl_today": pnl_today,
        }

        # Pull pulse_api aggregates via HTTP (internal) with graceful fallbacks
        dj_url = os.getenv("DJANGO_API_URL", "http://django:8000")
        # MT5 bridge base (public first, then internal)
        mt5_base = (
            os.getenv("MT5_URL")
            or os.getenv("MT5_API_URL")
            or "http://mt5:5001"
        )
        confluence = None
        risk_summary = None
        opportunities = []
        recent_journal_payload = []
        account_info = None
        open_positions = []
        risk_event = {}
        try:
            # risk summary
            rs = requests.get(f"{dj_url}/api/pulse/risk/summary", timeout=2)
            if rs.ok:
                risk_summary = rs.json()
        except Exception:
            risk_summary = None
        # MT5 account info (bridge)
        try:
            r = requests.get(f"{str(mt5_base).rstrip('/')}/account_info", timeout=2.5)
            if r.ok:
                data = r.json()
                if isinstance(data, dict) and data:
                    account_info = data
        except Exception:
            account_info = None
        # MT5 open positions (bridge)
        try:
            r = requests.get(f"{str(mt5_base).rstrip('/')}/positions_get", timeout=2.5)
            if r.ok:
                data = r.json()
                if isinstance(data, list):
                    open_positions = data
        except Exception:
            open_positions = []
        try:
            sig = requests.get(f"{dj_url}/api/pulse/signals/top?n=3", timeout=2)
            if sig.ok and isinstance(sig.json(), list):
                opportunities = sig.json()
        except Exception:
            opportunities = []
        try:
            jr = requests.get(f"{dj_url}/api/pulse/journal/recent?n=10", timeout=2)
            if jr.ok:
                jdata = jr.json()
                # Normalize to list
                if isinstance(jdata, list):
                    recent_journal_payload = jdata
                elif isinstance(jdata, dict) and isinstance(jdata.get("items"), list):
                    recent_journal_payload = jdata["items"]
        except Exception:
            # Fallback to local DB journal entries
            recent_journal = JournalEntry.objects.select_related('trade').order_by('-updated_at')[:10]
            recent_journal_payload = JournalEntrySerializer(recent_journal, many=True).data

        # ---- Profit Milestone Event (server-side "whisper") ----
        try:
            # Resolve equity and PnL
            equity_val = float((account_info or {}).get('equity', 0) or 0)
            profit_val = float((account_info or {}).get('profit', 0) or 0)
            # Load risk parameters from policies (if present)
            pol = load_policies() or {}
            risk_pol = pol.get('risk', {}) if isinstance(pol, dict) else {}
            daily_risk_pct = float(risk_pol.get('max_daily_loss_pct', 3.0))
            anticipated_trades = int(risk_pol.get('max_daily_trades', 5))
            daily_profit_pct = float(risk_pol.get('daily_profit_target_pct', 1.0))
            milestone_threshold = float(os.getenv('PROFIT_MILESTONE_THRESHOLD', '0.75'))
            
            daily_risk_amount = equity_val * (daily_risk_pct / 100.0)
            per_trade_risk = daily_risk_amount / max(anticipated_trades, 1)
            daily_profit_target_amt = equity_val * (daily_profit_pct / 100.0)
            milestone_amt = daily_profit_target_amt * milestone_threshold if daily_profit_target_amt else 0.0
            if profit_val > 0 and ((milestone_amt and profit_val >= milestone_amt) or (per_trade_risk and profit_val >= per_trade_risk)):
                risk_event = {
                    "event": "profit_milestone_reached",
                    "message": f"You've reached {int(milestone_threshold*100)}% of your daily target — consider protecting your position.",
                    "pnl": profit_val,
                    "milestone_amount": milestone_amt,
                    "per_trade_risk": per_trade_risk,
                }
                # Optional: publish a Telegram alert once per day (anti-spam via Redis key)
                if redis_lib is not None:
                    try:
                        rurl = os.getenv('REDIS_URL')
                        if rurl:
                            rcli = redis_lib.from_url(rurl)
                        else:
                            rcli = redis_lib.Redis(host=os.getenv('REDIS_HOST','redis'), port=int(os.getenv('REDIS_PORT',6379)))
                        cache_key = f"alert:profit_milestone:{(account_info or {}).get('login','') or 'acct'}:{timezone.now().strftime('%Y%m%d')}"
                        if not rcli.get(cache_key):
                            msg = {
                                "event": "profit_milestone_reached",
                                "text": f"🎯 Profit Milestone! PnL ${profit_val:,.2f}. Consider protecting your position.",
                                "actions": [
                                    {"label": "Move SL to BE", "action": "protect_breakeven"},
                                    {"label": "Trail SL (50%)", "action": "protect_trail_50"},
                                    {"label": "Ignore", "action": "ignore"}
                                ]
                            }
                            rcli.publish('telegram-alerts', json.dumps(msg))
                            rcli.setex(cache_key, 6*60*60, "1")  # 6 hours TTL
                            # Also append to today's discipline events list for trajectory markers
                            try:
                                ev_key = f"events:discipline:{timezone.now().strftime('%Y%m%d')}"
                                rcli.rpush(ev_key, json.dumps({
                                    'ts': timezone.now().isoformat(),
                                    'type': 'profit_milestone',
                                    'pnl': profit_val,
                                }))
                                rcli.expire(ev_key, 10*24*3600)
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            risk_event = {}

        payload = {
            "psychological_state": psych_payload,
            "confluence_score": confluence,
            "risk_metrics": risk_metrics,
            "risk_summary": risk_summary,
            "account_info": account_info or {},
            "open_positions": open_positions or [],
            "risk_event": risk_event,
            "opportunities": opportunities,
            "recent_journal": recent_journal_payload,
            "policies": load_policies(),
        }
        try:
            data = MirrorStateSerializer(payload).data
        except Exception:
            data = payload
        return Response(data)


class DisciplineSummaryView(views.APIView):
    """Compute and persist discipline metrics and events (7d).

    Returns:
      - today: score 0..100
      - yesterday: score 0..100 (if available)
      - seven_day: list of {date, score}
      - events_today: list of {ts, type, meta}
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Dependencies
        dj_url = os.getenv("DJANGO_API_URL", "http://django:8000")
        today = timezone.now().date()
        key_score = f"discipline:{today.strftime('%Y%m%d')}"
        key_series = "discipline:series:7d"
        events_key = f"events:discipline:{today.strftime('%Y%m%d')}"
        score_today = None
        seven = []
        events_today = []
        # Pull risk summary to compute score
        risk_summary = {}
        try:
            rs = requests.get(f"{dj_url}/api/pulse/risk/summary", timeout=2)
            if rs.ok:
                risk_summary = rs.json() or {}
        except Exception:
            risk_summary = {}
        # Compute score
        try:
            used = float(risk_summary.get('daily_risk_used', 0) or 0)
            warnings = risk_summary.get('warnings', []) or []
            score_today = max(0.0, min(100.0, 100.0 - min(40.0, used) - (len(warnings) * 8.0)))
        except Exception:
            score_today = 100.0
        # Persist in Redis and build 7d series
        if redis_lib is not None:
            try:
                rurl = os.getenv('REDIS_URL')
                if rurl:
                    rcli = redis_lib.from_url(rurl)
                else:
                    rcli = redis_lib.Redis(host=os.getenv('REDIS_HOST','redis'), port=int(os.getenv('REDIS_PORT',6379)))
                rcli.setex(key_score, 48*3600, str(score_today))
                # Append/update rolling series
                series_raw = rcli.lrange(key_series, 0, -1) or []
                # ensure unique per day by rewriting last if same date
                today_iso = today.isoformat()
                new_entry = json.dumps({'date': today_iso, 'score': score_today})
                if series_raw:
                    last = json.loads(series_raw[-1])
                    if last.get('date') == today_iso:
                        rcli.rpop(key_series)
                rcli.rpush(key_series, new_entry)
                rcli.ltrim(key_series, -7, -1)
                seven = [json.loads(x) for x in rcli.lrange(key_series, 0, -1)]
                events_today = [json.loads(x) for x in rcli.lrange(events_key, 0, -1)]
            except Exception:
                pass
        payload = {
            'today': score_today,
            'yesterday': seven[-2]['score'] if len(seven) >= 2 else None,
            'seven_day': seven,
            'events_today': events_today,
        }
        try:
            data = DisciplineSummarySerializer(payload).data
        except Exception:
            data = payload
        return Response(data)


class JournalEntryView(views.APIView):
    """Create/update JournalEntry linked to a Trade.

    POST JSON fields:
      - trade_id (required)
      - pre_trade_confidence, post_trade_feeling, notes (optional)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Optional token auth: if DJANGO_API_TOKEN is set, require it
        api_token = os.getenv("DJANGO_API_TOKEN", "").strip().strip('"')
        if api_token:
            auth = request.headers.get("Authorization", "")
            x_token = request.headers.get("X-API-Token", "")
            valid = False
            if auth.startswith("Token ") and auth.split(" ", 1)[1] == api_token:
                valid = True
            if x_token and x_token == api_token:
                valid = True
            if not valid:
                return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data or {}
        trade_id = data.get('trade_id')
        if not trade_id:
            return Response({"error": "trade_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            trade = Trade.objects.get(id=trade_id)
        except Trade.DoesNotExist:
            return Response({"error": "Trade not found"}, status=status.HTTP_404_NOT_FOUND)

        # Upsert
        journal, created = JournalEntry.objects.get_or_create(trade=trade)
        for f in ["pre_trade_confidence", "post_trade_feeling", "notes"]:
            if f in data:
                setattr(journal, f, data.get(f))
        journal.save()
        return Response(JournalEntrySerializer(journal).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ProtectPositionView(views.APIView):
    """Protect an open position via MT5 bridge.

    POST JSON fields:
      - action: 'protect_breakeven' | 'protect_trail_50'
      - ticket: optional (preferred)
      - symbol: optional (fallback if ticket omitted and only one position on symbol)
      - lock_ratio: optional float (0..1) for trailing lock-in ratio, default 0.5

    Auth: If DJANGO_API_TOKEN is set, require Token or X-API-Token header.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Optional token auth
        api_token = os.getenv("DJANGO_API_TOKEN", "").strip().strip('"')
        if api_token:
            auth = request.headers.get("Authorization", "")
            x_token = request.headers.get("X-API-Token", "")
            valid = False
            if auth.startswith("Token ") and auth.split(" ", 1)[1] == api_token:
                valid = True
            if x_token and x_token == api_token:
                valid = True
            if not valid:
                return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data or {}
        action = str(data.get('action', '')).strip()
        ticket = data.get('ticket')
        symbol = data.get('symbol')
        try:
            lock_ratio = float(data.get('lock_ratio', 0.5))
        except Exception:
            lock_ratio = 0.5
        lock_ratio = max(0.0, min(1.0, lock_ratio))

        if action not in ('protect_breakeven', 'protect_trail_50'):
            return Response({"error": "Unsupported action"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch open positions from MT5 bridge
        mt5_base = (
            os.getenv("MT5_URL")
            or os.getenv("MT5_API_URL")
            or "http://mt5:5001"
        )
        try:
            r = requests.get(f"{str(mt5_base).rstrip('/')}/positions_get", timeout=3.0)
            if not r.ok:
                return Response({"error": f"Bridge HTTP {r.status_code}"}, status=status.HTTP_502_BAD_GATEWAY)
            positions = r.json() or []
            if not isinstance(positions, list):
                positions = []
        except Exception as e:
            return Response({"error": f"Bridge error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        # Locate the target position
        pos = None
        if ticket is not None:
            try:
                tid = int(ticket)
            except Exception:
                return Response({"error": "Invalid ticket"}, status=status.HTTP_400_BAD_REQUEST)
            for p in positions:
                if int(p.get('ticket', -1)) == tid:
                    pos = p
                    break
        elif symbol:
            sym = str(symbol).upper()
            candidates = [p for p in positions if str(p.get('symbol','')).upper() == sym]
            if len(candidates) == 1:
                pos = candidates[0]
            elif len(candidates) > 1:
                return Response({"error": "Multiple positions for symbol; specify ticket"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "ticket or symbol required"}, status=status.HTTP_400_BAD_REQUEST)

        if not pos:
            return Response({"error": "Position not found"}, status=status.HTTP_404_NOT_FOUND)

        # Compute new SL
        try:
            price_open = float(pos.get('price_open'))
            typ = pos.get('type')  # numeric 0=BUY,1=SELL
            ptype = 'BUY' if int(typ) == 0 else 'SELL'
            sym = pos.get('symbol')
            volume = float(pos.get('volume'))
            current_profit = float(pos.get('profit') or 0.0)

            if action == 'protect_breakeven':
                new_sl = price_open
            else:
                # lock a fraction of current profit; if non-positive, reject
                if current_profit <= 0:
                    return Response({"error": "Cannot trail: non-positive profit"}, status=status.HTTP_400_BAD_REQUEST)
                lock_usd = current_profit * lock_ratio
                notional_usd = float(convert_lots_to_usd(sym, volume, price_open))
                commission = float(calculate_commission(notional_usd, sym))
                price_inc_comm, _ = get_price_at_pnl(
                    desired_pnl=lock_usd,
                    entry_price=price_open,
                    order_size_usd=notional_usd,
                    leverage=1.0,
                    type=ptype,
                    commission=commission,
                )
                new_sl = float(price_inc_comm)

            # Build a minimal position-like object for modify_sl_tp
            class _P: pass
            pobj = _P()
            pobj.ticket = int(pos.get('ticket'))
            pobj.symbol = sym
            pobj.type = int(typ)

            result = modify_sl_tp_position(pobj, sl=new_sl, tp=None)
            if result is None:
                return Response({"error": "Failed to modify SL"}, status=status.HTTP_502_BAD_GATEWAY)
            return Response({"ok": True, "ticket": pobj.ticket, "new_sl": new_sl, "action": action})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PositionsPartialCloseView(views.APIView):
    """Close part of a position via MT5 bridge.

    POST JSON:
      - ticket (int)
      - symbol (str)
      - fraction (float 0..1)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        api_token = os.getenv("DJANGO_API_TOKEN", "").strip().strip('"')
        if api_token:
            auth = request.headers.get("Authorization", "")
            x_token = request.headers.get("X-API-Token", "")
            valid = False
            if auth.startswith("Token ") and auth.split(" ", 1)[1] == api_token:
                valid = True
            if x_token and x_token == api_token:
                valid = True
            if not valid:
                return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data or {}
        try:
            ticket = int(data.get('ticket'))
            symbol = str(data.get('symbol'))
            fraction = float(data.get('fraction'))
        except Exception:
            return Response({"error": "ticket, symbol, fraction required"}, status=status.HTTP_400_BAD_REQUEST)
        mt5_base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
        try:
            r = requests.post(f"{mt5_base.rstrip('/')}/partial_close", json={'ticket': ticket, 'symbol': symbol, 'fraction': fraction}, timeout=6.0)
            if r.ok and isinstance(r.json(), dict) and r.json().get('ok'):
                return Response(r.json())
            return Response({'error': 'partial_close_failed', 'detail': getattr(r, 'text', '')}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class Healthz(View):
    """Ultra-light health endpoint that avoids ORM to prevent startup failures."""
    def get(self, request):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_ok = False
        payload = {
            "status": "ok" if db_ok else "degraded",
            "db": db_ok,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return JsonResponse(payload, status=200 if db_ok else 503)


# ------------------- Minimal Feed Endpoints (spec) -------------------
from rest_framework.permissions import AllowAny  # already imported but kept explicit


def _redis_client():
    if redis_lib is None:
        return None
    try:
        if os.getenv("REDIS_URL"):
            return redis_lib.from_url(os.getenv("REDIS_URL"))
        return redis_lib.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)))
    except Exception:
        return None


def _publish_feed(kind: str, payload: dict) -> None:
    r = _redis_client()
    if r is None:
        return
    try:
        doc = {"kind": kind, "ts": int(time.time()), "data": payload}
        r.publish("pulse.feeds", json.dumps(doc))
    except Exception:
        pass


class FeedBalanceView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        mt5_base = (
            os.getenv("MT5_URL")
            or os.getenv("MT5_API_URL")
            or "http://mt5:5001"
        )
        account_info = {}
        try:
            r = requests.get(f"{str(mt5_base).rstrip('/')}/account_info", timeout=1.5)
            if r.ok:
                account_info = r.json() or {}
                if isinstance(account_info, list) and account_info:
                    account_info = account_info[0]
        except Exception:
            account_info = {}

        try:
            balance = float(account_info.get("balance") or account_info.get("Balance") or 0.0)
        except Exception:
            balance = 0.0
        try:
            equity_prev = float(account_info.get("equity_prev") or 0.0)
        except Exception:
            equity_prev = 0.0

        # Optional: compute YTD % from a cached baseline if available
        pnl_ytd_pct = None
        try:
            r = _redis_client()
            if r is not None:
                key = f"balance:ytd:baseline:{datetime.now().year}"
                base = r.get(key)
                if base is None and balance:
                    r.setex(key, 180*24*3600, str(balance))
                elif base is not None:
                    b = float(base)
                    if b > 0:
                        pnl_ytd_pct = ((balance - b) / b) * 100.0
        except Exception:
            pass

        payload = {
            "balance_usd": balance,
            "pnl_total_pct": None,
            "pnl_inception_momentum_pct": None,
            "pnl_ytd_pct": pnl_ytd_pct,
            "markers": {
                "inception": None,
                "prev_close": equity_prev or None,
                "ath_balance": None,
                "atl_balance": None,
            },
            "awaiting": {
                "pnl_ytd_pct": pnl_ytd_pct is None,
                "pnl_inception_momentum_pct": True,
            },
        }
        _publish_feed("balance", payload)
        return Response(payload)


class FeedEquityView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        sod = _trading_day_start_utc()
        closed_today = Trade.objects.filter(close_time__gte=sod, close_time__isnull=False)
        pnl_today = sum([t.pnl or 0 for t in closed_today])
        # Pull account risk envelope for targets/exposure if available
        daily_target = None
        daily_loss = None
        risk_used = None
        exposure = None
        try:
            base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
            r = requests.get(f"{base}/api/v1/account/risk", timeout=1.2)
            if r.ok:
                risk = r.json() or {}
                daily_target = risk.get('target_amount')
                daily_loss = risk.get('loss_amount')
                ru = risk.get('used_pct')
                ex = risk.get('exposure_pct')
                if isinstance(ru, (int, float)):
                    risk_used = float(ru if ru <= 1 else ru/100.0)
                if isinstance(ex, (int, float)):
                    exposure = float(ex if ex <= 1 else ex/100.0)
        except Exception:
            pass
        pct_to_target = None
        try:
            if pnl_today >= 0 and daily_target and daily_target > 0:
                pct_to_target = min(1.0, float(pnl_today) / float(daily_target))
            elif pnl_today < 0 and daily_loss and daily_loss > 0:
                pct_to_target = -min(1.0, abs(float(pnl_today)) / float(daily_loss))
        except Exception:
            pct_to_target = None

        payload = {
            "session_pnl": pnl_today,
            "pct_to_target": pct_to_target,
            "risk_used_pct": risk_used,
            "exposure_pct": exposure,
            "markers": {
                "daily_target": daily_target,
                "daily_loss_limit": daily_loss,
                "account_drawdown_hard": None,
            },
        }
        _publish_feed("equity", payload)
        return Response(payload)


class EquitySeriesView(views.APIView):
    """Intraday equity series derived from closed trades today.

    Returns JSON: { sod_equity?: number, points: [{ ts: ISO8601, pnl: number }] }
    pnl is cumulative USD P&L for the session (>= 0: profit, < 0: loss).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        start_utc, end_utc, _ = session_bounds()
        qs = Trade.objects.filter(close_time__gte=start_utc, close_time__lt=end_utc, close_time__isnull=False).order_by('close_time')
        points = []
        cum = 0.0
        for t in qs:
            try:
                cum += float(t.pnl or 0.0)
                points.append({
                    'ts': t.close_time.isoformat() if t.close_time else None,
                    'pnl': cum,
                })
            except Exception:
                continue
        # Optional: include SoD equity if available from account risk
        sod_equity = None
        try:
            base = os.getenv('DJANGO_EXTERNAL_BASE') or ''
            # Prefer internal resolution; fallback to env base if provided
            from django.urls import reverse
            url = (base.rstrip('/') + reverse('account-risk')) if base else None
            if url:
                r = requests.get(url, timeout=1.0)
                if r.ok:
                    data = r.json() or {}
                    se = data.get('sod_equity')
                    if isinstance(se, (int, float)):
                        sod_equity = float(se)
        except Exception:
            pass
        out = {'points': points}
        if sod_equity is not None:
            out['sod_equity'] = sod_equity
        _publish_feed('equity_series', out)
        return Response(out)


class EquityTodayView(views.APIView):
    """Return intraday equity time series by adding SoD equity to cumulative PnL.

    Shape: [{ ts: ISO8601, equity: number }]
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Reuse EquitySeriesView logic to compute cumulative PnL and SoD equity
        try:
            es = EquitySeriesView()
            resp = es.get(request)
            data = resp.data if hasattr(resp, 'data') else {}
            points = data.get('points') if isinstance(data, dict) else []
            sod_equity = data.get('sod_equity') if isinstance(data, dict) else None
        except Exception:
            points, sod_equity = [], None
        out = []
        base = float(sod_equity) if isinstance(sod_equity, (int, float)) else None
        for p in (points or []):
            ts = p.get('ts')
            pnl = p.get('pnl')
            try:
                eq = (base + float(pnl)) if (base is not None and pnl is not None) else None
            except Exception:
                eq = None
            out.append({'ts': ts, 'equity': eq})
        return Response(out)

class FeedTradeView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        sod = _trading_day_start_utc()
        realized = 0.0
        try:
            realized = float(sum([(t.pnl or 0.0) for t in Trade.objects.filter(close_time__gte=sod)]))
        except Exception:
            realized = 0.0
        # Unrealized from positions proxy (best-effort)
        unrealized = None
        try:
            base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
            r = requests.get(f"{base}/api/v1/account/positions", timeout=1.2)
            if r.ok:
                arr = r.json() or []
                if isinstance(arr, list):
                    unrealized = float(sum([float(p.get('pnl') or 0.0) for p in arr]))
        except Exception:
            unrealized = None
        # Profit efficiency: ratio of realized vs sum of positive peaks (ProfitHorizon logic)
        eff = None
        try:
            closed = Trade.objects.exclude(close_time__isnull=True).order_by('-close_time')[:50]
            total_peak = 0.0
            total_pnl = 0.0
            for t in closed:
                pnlv = float(t.pnl or 0)
                peak = float(t.max_profit or 0)
                if peak > 0 and pnlv > 0:
                    total_peak += peak
                    total_pnl += pnlv
            if total_peak > 0:
                eff = total_pnl / total_peak
        except Exception:
            eff = None
        payload = {
            "pnl_day_vs_goal": None,
            "realized_usd": realized,
            "unrealized_usd": unrealized,
            "profit_efficiency": eff,
            "eff_trend_15m": 0,
        }
        _publish_feed("trade", payload)
        return Response(payload)


class FeedBehaviorView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        latest_psych = PsychologicalState.objects.order_by('-timestamp').first()
        discipline = getattr(latest_psych, 'discipline_score', None) if latest_psych else None
        eff = getattr(latest_psych, 'profit_efficiency', None) if latest_psych else None
        payload = {
            "discipline_score": discipline,
            "patience_index_dev": None,
            "profit_efficiency": eff,
            "conviction": {"high_win": None, "low_win": None},
        }
        _publish_feed("behavior", payload)
        return Response(payload)


class ProfitHorizonView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            limit = int(request.GET.get("limit", "20"))
        except Exception:
            limit = 20
        qs = Trade.objects.exclude(close_time__isnull=True).order_by('-close_time')[:limit]
        out = []
        for t in qs:
            try:
                dur = int(((t.close_time - t.entry_time).total_seconds()) // 60) if t.entry_time and t.close_time else None
            except Exception:
                dur = None
            # USD values as fallback; R-multiples require per-trade risk, not stored here
            pnl_usd = float(t.pnl or 0)
            peak_usd = float(t.max_profit or 0)
            out.append({
                "id": str(t.id),
                "dur_min": dur,
                "pnl_r": None,
                "peak_r": None,
                "pnl_usd": pnl_usd,
                "peak_usd": peak_usd,
            })
        _publish_feed("profit-horizon", {"items": out})
        return Response(out)


class TradeHistoryView(views.APIView):
    """Simplified trade history for behavioral analysis UIs.

    GET /api/v1/trades/history?symbol=EURUSD
    Returns: [{ id, ts, symbol, direction, entry, exit, pnl, status }]
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        from datetime import datetime, timedelta
        symbol = request.GET.get('symbol')
        date_from = request.GET.get('date_from')  # ISO date or datetime
        date_to = request.GET.get('date_to')
        pnl_min = request.GET.get('pnl_min')
        pnl_max = request.GET.get('pnl_max')
        source = (request.GET.get('source') or '').lower()

        # MT5-only source (bypass DB and fetch live from bridge)
        if source == 'mt5':
            try:
                # Resolve date window
                now = timezone.now()
                try:
                    dfrom = datetime.fromisoformat(date_from) if date_from else (now - timedelta(days=7))
                except Exception:
                    dfrom = now - timedelta(days=7)
                try:
                    dto = datetime.fromisoformat(date_to) if date_to else now
                except Exception:
                    dto = now
                base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
                url = f"{str(base).rstrip('/')}/history_deals_get"
                params = {
                    'from_date': dfrom.isoformat(),
                    'to_date': dto.isoformat(),
                }
                r = requests.get(url, params=params, timeout=3.0)
                items = r.json() if r.ok else []
                out = []
                if isinstance(items, list):
                    for it in items:
                        try:
                            if symbol and str(it.get('symbol') or '') != str(symbol):
                                continue
                            ts_val = it.get('time') or it.get('timestamp')
                            try:
                                ts_iso = datetime.fromtimestamp(float(ts_val), tz=timezone.utc).isoformat()
                            except Exception:
                                ts_iso = str(ts_val)
                            dline = {
                                'id': it.get('ticket') or it.get('position') or it.get('order') or None,
                                'ts': ts_iso,
                                'symbol': it.get('symbol'),
                                'direction': 'BUY' if str(it.get('type') or '').upper().endswith('BUY') else 'SELL' if str(it.get('type') or '').upper().endswith('SELL') else None,
                                'entry': it.get('price'),
                                'exit': None,
                                'pnl': it.get('profit'),
                                'status': 'deal',
                            }
                            # PnL filters
                            try:
                                if pnl_min is not None and dline['pnl'] is not None and float(dline['pnl']) < float(pnl_min):
                                    continue
                                if pnl_max is not None and dline['pnl'] is not None and float(dline['pnl']) > float(pnl_max):
                                    continue
                            except Exception:
                                pass
                            out.append(dline)
                        except Exception:
                            continue
                return Response(out)
            except Exception:
                return Response([])

        qs = Trade.objects.all().order_by('-entry_time')
        if symbol:
            qs = qs.filter(symbol=str(symbol))
        # Date range filters (inclusive)
        try:
            if date_from:
                try:
                    dtf = datetime.fromisoformat(date_from)
                except Exception:
                    dtf = timezone.make_aware(datetime.strptime(date_from, "%Y-%m-%d"))
                qs = qs.filter(entry_time__gte=dtf)
            if date_to:
                try:
                    dtt = datetime.fromisoformat(date_to)
                except Exception:
                    # end of day
                    base = datetime.strptime(date_to, "%Y-%m-%d")
                    dtt = timezone.make_aware(base + timedelta(hours=23, minutes=59, seconds=59))
                qs = qs.filter(entry_time__lte=dtt)
        except Exception:
            pass
        # PnL filters
        try:
            if pnl_min is not None:
                qs = qs.filter(pnl__gte=float(pnl_min))
        except Exception:
            pass
        try:
            if pnl_max is not None:
                qs = qs.filter(pnl__lte=float(pnl_max))
        except Exception:
            pass
        out = []
        for t in qs[:500]:
            try:
                out.append({
                    'id': t.id,
                    'ts': (t.close_time or t.entry_time).isoformat() if (t.entry_time or t.close_time) else None,
                    'symbol': t.symbol,
                    'direction': t.type,
                    'entry': float(t.entry_price or 0.0),
                    'exit': float(t.close_price) if t.close_price is not None else None,
                    'pnl': float(t.pnl) if t.pnl is not None else None,
                    'status': 'closed' if t.close_time else 'open',
                })
            except Exception:
                continue
        # Optional fallback: if DB is empty and no explicit source provided, proxy to MT5 history
        try:
            fallback_flag = str(os.getenv('TRADE_HISTORY_FALLBACK_TO_MT5') or 'true').lower() != 'false'
        except Exception:
            fallback_flag = True
        if fallback_flag and not out:
            # Reuse MT5 branch with the same filters
            try:
                req = request._request
                req.GET = req.GET.copy()
                req.GET['source'] = 'mt5'
                if symbol:
                    req.GET['symbol'] = symbol
                if date_from:
                    req.GET['date_from'] = date_from
                if date_to:
                    req.GET['date_to'] = date_to
                if pnl_min is not None:
                    req.GET['pnl_min'] = str(pnl_min)
                if pnl_max is not None:
                    req.GET['pnl_max'] = str(pnl_max)
                return TradeHistoryView().get(request)
            except Exception:
                pass
        return Response(out)


class TradesRecentView(views.APIView):
    """Recent trades with minimal normalized fields.

    GET /api/v1/trades/recent?limit=200
    Returns [{ id, ts_open, ts_close, symbol, side, entry, exit, pnl, rr, strategy, session }]
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            limit = int(request.GET.get('limit', '200'))
        except Exception:
            limit = 200
        limit = max(1, min(1000, limit))
        qs = Trade.objects.all().order_by('-entry_time')[:limit]
        out = []
        for t in qs:
            try:
                out.append({
                    'id': t.id,
                    'ts_open': t.entry_time.isoformat() if t.entry_time else None,
                    'ts_close': t.close_time.isoformat() if t.close_time else None,
                    'symbol': t.symbol,
                    'side': (t.type or '').lower(),
                    'entry': float(t.entry_price) if t.entry_price is not None else None,
                    'exit': float(t.close_price) if t.close_price is not None else None,
                    'pnl': float(t.pnl) if t.pnl is not None else None,
                    'rr': None,
                    'strategy': t.strategy,
                    'session': None,
                })
            except Exception:
                continue
        return Response(out)


class ActionsQueryView(views.APIView):
    """Consolidated query endpoint (prototype). Not documented in OpenAPI actions cap.

    POST { type: str, payload: dict }
    type ∈ { market_snapshot, pulse_status, trades_recent, behavior_events, equity_today, session_boot, trades_history_mt5 }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Read-only Actions via GET to avoid consent prompts in some runtimes.

        Query params: ?type=<verb>&symbol=...&limit=...&timeframe=...&date_from=...&date_to=...&pnl_min=...&pnl_max=...
        Supported verbs: session_boot, trades_recent, trades_history_mt5, account_info, account_positions,
                         account_risk, equity_today, market_mini, market_symbols, market_calendar_next,
                         market_regime, liquidity_map, state_snapshot, journal_recent, whisper_suggest
        """
        typ = str(request.GET.get('type') or '').strip()
        try:
            if typ == 'session_boot':
                # Map to POST handler logic with default payload extracted from query params
                req = request._request
                req.data = {
                    'type': 'session_boot',
                    'payload': {
                        'limit_trades': request.GET.get('limit') or request.GET.get('limit_trades'),
                        'include_positions': request.GET.get('include_positions'),
                        'include_equity': request.GET.get('include_equity'),
                        'include_risk': request.GET.get('include_risk'),
                    },
                }
                return self.post(request)
            if typ == 'trades_recent':
                req = request._request
                req.GET = req.GET.copy()
                if request.GET.get('limit'):
                    req.GET['limit'] = str(request.GET.get('limit'))
                return TradesRecentView().get(request)
            if typ == 'trades_history_mt5':
                req = request._request
                req.GET = req.GET.copy()
                req.GET['source'] = 'mt5'
                for k in ('symbol','date_from','date_to','pnl_min','pnl_max'):
                    v = request.GET.get(k)
                    if v is not None:
                        req.GET[k] = str(v)
                return TradeHistoryView().get(request)
            if typ == 'account_info':
                return AccountInfoView().get(request)
            if typ == 'account_positions':
                return PositionsProxyView().get(request)
            if typ == 'account_risk':
                return AccountRiskView().get(request)
            if typ == 'equity_today':
                return EquityTodayView().get(request)
            if typ == 'market_mini' or typ == 'market_snapshot':
                return MarketMiniView().get(request)
            if typ == 'market_symbols':
                return MarketSymbolsView().get(request)
            if typ == 'market_calendar_next':
                req = request._request
                req.GET = req.GET.copy()
                if request.GET.get('limit'):
                    req.GET['limit'] = str(request.GET.get('limit'))
                return MarketCalendarNextView().get(request)
            if typ == 'market_regime':
                return MarketRegimeView().get(request)
            if typ == 'liquidity_map':
                req = request._request
                req.GET = req.GET.copy()
                if request.GET.get('symbol'):
                    req.GET['symbol'] = str(request.GET.get('symbol'))
                if request.GET.get('timeframe'):
                    req.GET['timeframe'] = str(request.GET.get('timeframe'))
                return LiquidityMapView().get(request)
            if typ == 'state_snapshot':
                return StateSnapshotView().get(request)
            if typ == 'journal_recent':
                req = request._request
                req.GET = req.GET.copy()
                if request.GET.get('limit'):
                    req.GET['limit'] = str(request.GET.get('limit'))
                return JournalRecentView().get(request)
            if typ == 'whisper_suggest':
                # Map to POST handler for consistent behavior (uses GET params)
                req = request._request
                req.data = {
                    'type': 'whisper_suggest',
                    'payload': {
                        'symbol': request.GET.get('symbol'),
                        'user_id': request.GET.get('user_id'),
                    },
                }
                return self.post(request)
            return Response({'error': f'unknown type: {typ}'}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def post(self, request):
        data = request.data or {}
        typ = str(data.get('type') or '')
        payload = data.get('payload') or {}
        # Back-compat: allow flat fields when payload is omitted by the client/tooling
        try:
            if not payload and typ in ('position_close', 'position_modify', 'position_open', 'position_hedge'):
                flat = {}
                # Collect common fields if present at top-level
                for k in ('ticket', 'fraction', 'volume', 'sl', 'tp', 'symbol', 'side', 'comment'):
                    if k in data and data.get(k) is not None:
                        flat[k] = data.get(k)
                if flat:
                    payload = flat
        except Exception:
            pass
        try:
            if typ == 'session_boot':
                # Composite boot snapshot for LLM initialization
                # Payload: { limit_trades?: int, include_positions?: bool, include_equity?: bool, include_risk?: bool }
                # Optional cache: use Redis with TTL from env SESSION_BOOT_TTL (seconds)
                ttl = 0
                try:
                    ttl = int(os.getenv('SESSION_BOOT_TTL') or os.getenv('ACTIONS_SESSION_BOOT_TTL') or 0)
                except Exception:
                    ttl = 0
                cache_key = None
                if ttl and redis_lib is not None:
                    try:
                        user_id = str(payload.get('user_id') or request.META.get('REMOTE_USER') or 'global')
                        cache_key = f"session_boot:{user_id}"
                        rcli = _redis_client()
                        if rcli is not None:
                            raw = rcli.get(cache_key)
                            if raw:
                                try:
                                    cached = _json.loads(raw)
                                    return Response(cached)
                                except Exception:
                                    pass
                    except Exception:
                        cache_key = None
                limit = 10
                try:
                    limit = int(payload.get('limit_trades') or payload.get('limit') or 10)
                except Exception:
                    limit = 10
                include_positions = str(payload.get('include_positions') if payload.get('include_positions') is not None else True).lower() != 'false'
                include_equity = str(payload.get('include_equity') if payload.get('include_equity') is not None else True).lower() != 'false'
                include_risk = str(payload.get('include_risk') if payload.get('include_risk') is not None else True).lower() != 'false'

                # Trades (recent N)
                req = request._request
                req.GET = req.GET.copy()
                req.GET['limit'] = str(limit)
                trades = []
                try:
                    trades = TradesRecentView().get(request).data or []
                except Exception:
                    trades = []

                # Positions (proxy)
                positions = []
                if include_positions:
                    try:
                        positions = PositionsProxyView().get(request).data or []
                    except Exception:
                        positions = []

                # Equity summary (balance + optional YTD; drawdown est from SoD)
                equity = None
                if include_equity:
                    equity = { 'balance_usd': None, 'pnl_ytd_pct': None, 'drawdown_pct': None }
                    try:
                        acct = AccountInfoView().get(request).data or {}
                    except Exception:
                        acct = {}
                    try:
                        risk_env = AccountRiskView().get(request).data or {}
                    except Exception:
                        risk_env = {}
                    try:
                        bal = acct.get('balance') or acct.get('equity')
                        equity['balance_usd'] = float(bal) if isinstance(bal, (int, float)) else None
                    except Exception:
                        pass
                    # YTD pnl pct is currently exposed via FeedBalanceView markers; best-effort None if unavailable
                    try:
                        fb = FeedBalanceView().get(request).data or {}
                        ytd = fb.get('pnl_ytd_pct')
                        equity['pnl_ytd_pct'] = float(ytd) if isinstance(ytd, (int, float)) else None
                    except Exception:
                        pass
                    # Drawdown vs SoD (session): negative percentage of loss relative to SoD
                    try:
                        sod = risk_env.get('sod_equity')
                        eq_now = acct.get('equity') or acct.get('balance')
                        if isinstance(sod, (int, float)) and isinstance(eq_now, (int, float)) and sod > 0:
                            dd = (float(eq_now) - float(sod)) / float(sod) * 100.0
                            # If below SoD, report negative; else 0 or positive drift
                            equity['drawdown_pct'] = float(dd) if dd < 0 else 0.0
                    except Exception:
                        pass

                # Risk envelope
                risk = None
                if include_risk:
                    try:
                        rk = AccountRiskView().get(request).data or {}
                        # Normalize risk fields and coerce %-like fields to numeric
                        def _num(x):
                            try:
                                return float(x)
                            except Exception:
                                return None
                        risk = {
                            'daily_profit_pct': _num(rk.get('daily_profit_pct')),
                            'daily_risk_pct': _num(rk.get('daily_risk_pct')),
                            'used_pct': _num(rk.get('used_pct')),
                            'exposure_pct': _num(rk.get('exposure_pct')),
                        }
                    except Exception:
                        risk = None

                out_obj = {
                    'trades': trades,
                    'positions': (positions if include_positions else []),
                    'equity': (equity if include_equity else None),
                    'risk': (risk if include_risk else None),
                }
                # Store in cache if enabled
                if ttl and redis_lib is not None and cache_key:
                    try:
                        rcli = _redis_client()
                        if rcli is not None:
                            rcli.setex(cache_key, int(ttl), _json.dumps(out_obj))
                    except Exception:
                        pass
                return Response(out_obj)
            if typ == 'trades_recent':
                req = request._request
                req.GET = req.GET.copy()
                req.GET['limit'] = str(payload.get('limit') or 200)
                return TradesRecentView().get(request)
            if typ == 'trades_history_mt5':
                # Proxy to TradeHistoryView with source=mt5 and optional filters
                req = request._request
                req.GET = req.GET.copy()
                req.GET['source'] = 'mt5'
                # Optional filters: symbol, date_from, date_to, pnl_min, pnl_max
                for k in ('symbol', 'date_from', 'date_to', 'pnl_min', 'pnl_max'):
                    v = payload.get(k)
                    if v is not None:
                        req.GET[k] = str(v)
                return TradeHistoryView().get(request)
            if typ == 'behavior_events':
                return BehaviorEventsTodayView().get(request)
            if typ == 'equity_today':
                return EquityTodayView().get(request)
            if typ == 'pulse_status':
                # Proxy to pulse status (symbol required)
                from app.nexus.pulse.views import PulseStatus  # type: ignore
                req = request._request
                req.GET = req.GET.copy()
                sym = payload.get('symbol') or 'XAUUSD'
                req.GET['symbol'] = sym
                return PulseStatus().get(request)
            if typ == 'market_snapshot':
                # Minimal: reuse market/mini
                return MarketMiniView().get(request)
            if typ == 'state_snapshot':
                return StateSnapshotView().get(request)
            if typ == 'account_info':
                return AccountInfoView().get(request)
            if typ == 'account_positions':
                return PositionsProxyView().get(request)
            if typ == 'account_risk':
                return AccountRiskView().get(request)
            if typ == 'market_mini':
                return MarketMiniView().get(request)
            if typ == 'market_symbols':
                return MarketSymbolsView().get(request)
            if typ == 'market_calendar_next':
                req = request._request
                req.GET = req.GET.copy()
                if payload.get('limit') is not None:
                    req.GET['limit'] = str(payload.get('limit'))
                return MarketCalendarNextView().get(request)
            if typ == 'market_regime':
                return MarketRegimeView().get(request)
            if typ == 'liquidity_map':
                # payload: { symbol?, timeframe? }
                req = request._request
                req.GET = req.GET.copy()
                if payload.get('symbol'):
                    req.GET['symbol'] = str(payload.get('symbol'))
                if payload.get('timeframe'):
                    req.GET['timeframe'] = str(payload.get('timeframe'))
                return LiquidityMapView().get(request)
            if typ == 'opportunity_priority_items':
                # payload: { candidates?, symbols?, constraints? }
                req = request._request
                req.data = payload
                return PriorityItemsView().post(request)
            if typ == 'journal_recent':
                req = request._request
                req.GET = req.GET.copy()
                if payload.get('limit') is not None:
                    req.GET['limit'] = str(payload.get('limit'))
                return JournalRecentView().get(request)
            if typ == 'journal_append':
                req = request._request
                req.data = payload
                return JournalEntryPostView().post(request)
            if typ == 'position_open':
                # payload: { symbol, volume, side, sl?, tp?, comment? }
                req = request._request
                req.data = payload
                return OrderMarketProxyView().post(request)
            if typ == 'position_close':
                # { ticket, fraction?, volume? }
                try:
                    from .orders_service import close_position_partial_or_full, get_position
                except Exception:
                    return Response({'error': 'service_unavailable'}, status=503)
                ticket = payload.get('ticket')
                if ticket is None:
                    return Response({'error': 'ticket required'}, status=400)
                try:
                    pos = get_position(ticket)
                    # Do not hard-fail if position lookup endpoint is degraded; let the bridge decide.
                    # If pos is empty, proceed with best-effort close via proxy which can resolve volume itself.
                except Exception:
                    pass
                ok, data = close_position_partial_or_full(
                    int(ticket), fraction=payload.get('fraction'), volume=payload.get('volume'),
                    idempotency_key=request.headers.get('X-Idempotency-Key')
                )
                return Response(data, status=200 if ok else 400)
            if typ == 'position_modify':
                # { ticket, sl?, tp? }
                try:
                    from .tasks import modify_position_task
                except ImportError:
                    return Response({'error': 'service_unavailable'}, status=503)
                ticket = payload.get('ticket')
                if ticket is None:
                    return Response({'error': 'ticket required'}, status=400)
                sl = payload.get('sl')
                tp = payload.get('tp')
                if sl is None and tp is None:
                    return Response({'error': 'sl or tp required'}, status=400)
                
                # Asynchronously execute the task
                modify_position_task.delay(int(ticket), sl=sl, tp=tp)
                
                return Response({'status': 'accepted', 'ticket': ticket}, status=status.HTTP_202_ACCEPTED)
            if typ == 'position_hedge':
                # { ticket, volume? }
                try:
                    from .orders_service import get_position, get_account_info, place_market_order
                except Exception:
                    return Response({'error': 'service_unavailable'}, status=503)
                ticket = payload.get('ticket')
                if ticket is None:
                    return Response({'error': 'ticket required'}, status=400)
                pos = get_position(ticket)
                if not pos:
                    return Response({'error': f'position {ticket} not found'}, status=404)
                ptype = pos.get('type')
                try:
                    pnum = int(ptype)
                    side = 'sell' if pnum == 0 else 'buy'
                except Exception:
                    side = 'sell' if str(ptype).lower().startswith('buy') else 'buy'
                vol = payload.get('volume') or pos.get('volume')
                ok, data = place_market_order(symbol=pos.get('symbol'), volume=float(vol), side=side,
                                              comment=f'hedge ticket={ticket}',
                                              idempotency_key=request.headers.get('X-Idempotency-Key'))
                acct = get_account_info() or {}
                if ok and str(acct.get('mode')).lower().startswith('net'):
                    data['note'] = 'Account likely in netting mode; hedge nets exposure.'
                return Response(data, status=200 if ok else 400)
            if typ == 'whisper_suggest':
                # Heuristic-driven quick whisper; best-effort inputs
                try:
                    from whisper_engine import WhisperEngine, State  # type: ignore
                except Exception:
                    return Response({"message": None, "heuristics": []})
                user_id = str(payload.get('user_id') or request.META.get('REMOTE_USER') or 'local')
                symbol = str(payload.get('symbol') or 'XAUUSD')
                # Pull mirror and risk (best-effort)
                ms = MirrorStateView().get(request).data or {}
                rk = AccountRiskView().get(request).data or {}
                # Pulse status
                req = request._request
                req.GET = req.GET.copy()
                req.GET['symbol'] = symbol
                try:
                    from app.nexus.pulse.views import PulseStatus  # type: ignore
                    ps = PulseStatus().get(request).data or {}
                except Exception:
                    ps = {}
                # Trades today count (within session)
                start_utc, end_utc, _ = session_bounds()
                try:
                    n_trades = Trade.objects.filter(entry_time__gte=start_utc).count()
                except Exception:
                    n_trades = 0
                # Build state
                confluence = float(ps.get('confidence') or 0.0) * 100.0
                patience_score = float(ms.get('discipline') or 80.0)  # placeholder; mirror may not expose patience score
                # No baseline delta → set 0
                st_obj = State(
                    confluence=confluence,
                    confluence_trend_up=False,
                    patience_index=patience_score,
                    patience_drop_pct=0.0,
                    loss_streak=0,
                    window_minutes=30,
                    recent_winrate_similar=0.5,
                    hard_cooldown_active=False,
                    risk_budget_used_pct=float((rk.get('used_pct') or 0.0) if isinstance(rk.get('used_pct'), (int, float)) else 0.0) / (100.0 if (isinstance(rk.get('used_pct'), (int, float)) and rk.get('used_pct') > 1) else 1.0),
                    trades_today=int(n_trades),
                    user_id=user_id,
                )
                engine = WhisperEngine(cfg={})
                hs = engine.evaluate(st_obj)
                from whisper_engine import serialize_whispers  # type: ignore
                top_msg = hs[0].message if hs else None
                return Response({"message": top_msg, "heuristics": serialize_whispers(hs), "meta": {"user_id": user_id, "symbol": symbol}})
            return Response({'error': 'unknown type'}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ActionsMutateView(views.APIView):
    """Consolidated mutation endpoint (prototype). Not documented in OpenAPI to keep cap.

    POST { type: str, payload: dict }
    type ∈ { alert_send, risk_update, note_create }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        typ = str(data.get('type') or '')
        payload = data.get('payload') or {}
        try:
            if typ == 'note_create':
                # Map to journal entry
                req = request._request
                req.data = payload
                return JournalEntryPostView().post(request)
            # alert_send / risk_update could be wired later
            return Response({'ok': False, 'note': 'not_implemented'}, status=501)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ActionsSpecView(views.APIView):
    """Serve the slim Actions OpenAPI spec (text/yaml) for LLM manifests.

    Path: /openapi.actions.yaml
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.http import HttpResponse
        from pathlib import Path
        candidates = []
        here = Path(__file__).resolve()
        # Search upwards for the file
        for i in range(1, 10):
            candidates.append(here.parents[i-1] / 'openapi.actions.yaml')
        for path in candidates:
            try:
                if path.exists():
                    txt = path.read_text(encoding='utf-8')
                    return HttpResponse(txt, content_type='text/yaml; charset=utf-8')
            except Exception:
                continue
        return HttpResponse('# actions spec not found', content_type='text/yaml; charset=utf-8', status=404)


class StateSnapshotView(views.APIView):
    """Consolidated state snapshot for LLMs/dashboards.

    GET /api/v1/state/snapshot -> {
      mirror: {...},
      patterns: {...},
      risk: {...},
      equity: {...}
    }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            mirror = MirrorStateView().get(request).data or {}
        except Exception:
            mirror = {}
        try:
            patterns = BehavioralPatternsView().get(request).data or {}
        except Exception:
            patterns = {}
        try:
            risk = AccountRiskView().get(request).data or {}
        except Exception:
            risk = {}
        try:
            equity = FeedEquityView().get(request).data or {}
        except Exception:
            equity = {}
        return Response({
            'mirror': mirror,
            'patterns': patterns,
            'risk': risk,
            'equity': equity,
        })


class MirrorStateView(views.APIView):
    """Minimal behavioral mirror state for the concentric dial.

    Returns keys:
      - patience_ratio (-0.5..+0.5)
      - discipline (0..100)
      - conviction (0..100)
      - efficiency (0..100)
      - pnl_norm (-1..+1)
    Any missing metric is omitted or set to null (UI shows neutral track).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        now = timezone.now()
        sod = _trading_day_start_utc(now)

        payload = {}

        # Patience ratio: compare today's inter-trade interval EMA vs simple baseline (last 7 days median)
        try:
            last_week = now - timezone.timedelta(days=7)
            qs_hist = (
                Trade.objects.filter(entry_time__gte=last_week)
                .exclude(entry_time__isnull=True)
                .order_by("entry_time")
            )
            times = [t.entry_time for t in qs_hist]
            deltas_hist = [
                (times[i] - times[i - 1]).total_seconds() / 60.0 for i in range(1, len(times))
            ]
            baseline = statistics.median(deltas_hist) if deltas_hist else None

            qs_today = (
                Trade.objects.filter(entry_time__gte=sod)
                .exclude(entry_time__isnull=True)
                .order_by("entry_time")
            )
            times_today = [t.entry_time for t in qs_today]
            deltas_today = [
                (times_today[i] - times_today[i - 1]).total_seconds() / 60.0
                for i in range(1, len(times_today))
            ]
            # Simple EMA with alpha=0.2
            if deltas_today:
                ema = deltas_today[0]
                for x in deltas_today[1:]:
                    ema = 0.2 * x + 0.8 * ema
            else:
                ema = None
            if baseline and ema:
                ratio = (ema - baseline) / baseline
                payload["patience_ratio"] = max(-0.5, min(0.5, ratio))
                # Provide descriptive stats for UI drawers
                payload["patience_median_min"] = float(ema)
                if deltas_today:
                    payload["patience_p25_min"] = float(sorted(deltas_today)[max(0, int(0.25 * (len(deltas_today) - 1)))])
                    payload["patience_p75_min"] = float(sorted(deltas_today)[max(0, int(0.75 * (len(deltas_today) - 1)))])
        except Exception:
            pass

        # Discipline: event-ledger if available in Redis events list; else cached score
        try:
            if redis_lib is not None:
                r = _redis_client()
                if r is not None:
                    DISCIPLINE_WEIGHTS = {
                        "low_confluence_entry": -15,
                        "override_cooldown": -25,
                        "size_up_after_loss": -10,
                        "overtrade_burst": -10,
                        "closed_winner_early": -5,
                        "journaled_reason": 2,
                        "size_down_after_loss": 5,
                        "respected_cooldown": 5,
                    }
                    events_key = f"events:discipline:{now.date().strftime('%Y%m%d')}"
                    ev_raw = r.lrange(events_key, 0, -1) or []
                    base = 100
                    deltas = []
                    for b in ev_raw:
                        try:
                            e = json.loads(b)
                        except Exception:
                            e = {}
                        kind = e.get("kind")
                        w = int(DISCIPLINE_WEIGHTS.get(kind, 0))
                        if w:
                            base += w
                            deltas.append({"kind": kind, "delta": w, "ts": e.get("ts")})
                    if deltas:
                        payload["discipline"] = max(0, min(100, base))
                        payload["discipline_deltas"] = deltas
                    if "discipline" not in payload:
                        key_score = f"discipline:{now.date().strftime('%Y%m%d')}"
                        raw = r.get(key_score)
                        if raw:
                            payload["discipline"] = float(raw)
        except Exception:
            pass

        # Conviction: hi-confidence win rate (top) and low-confidence loss rate (bottom) over last N
        try:
            N = 20
            high = (
                JournalEntry.objects.select_related('trade')
                .filter(pre_trade_confidence__isnull=False, trade__close_time__isnull=False)
                .order_by('-created_at')[:N]
            )
            hi = [j for j in high if (j.pre_trade_confidence or 0) >= 70]
            lo = [j for j in high if (j.pre_trade_confidence or 0) <= 30]
            if hi:
                wins = sum(1 for j in hi if (j.trade.pnl or 0) > 0)
                payload["conviction_hi_win"] = int(100.0 * wins / max(1, len(hi)))
            if lo:
                losses = sum(1 for j in lo if (j.trade.pnl or 0) < 0)
                payload["conviction_lo_loss"] = int(100.0 * losses / max(1, len(lo)))
        except Exception:
            pass

        # Efficiency: average captured vs peak favorable excursion (last N closed)
        try:
            N2 = 20
            closed = Trade.objects.exclude(close_time__isnull=True).order_by('-close_time')[:N2]
            ratios = []
            for t in closed:
                pnl = float(t.pnl or 0)
                peak = float(t.max_profit or 0)
                if peak > 0 and pnl > 0:
                    ratios.append(max(0.0, min(1.0, pnl / peak)))
            if ratios:
                payload["efficiency"] = int(100.0 * (sum(ratios) / len(ratios)))
        except Exception:
            pass

        # PnL normalized vs daily target/loss limits
        try:
            closed_today = Trade.objects.filter(close_time__gte=sod, close_time__isnull=False)
            pnl_today = float(sum([t.pnl or 0 for t in closed_today]))
            # Resolve equity from MT5 bridge (fallback None)
            mt5_base = (
                os.getenv("MT5_URL")
                or os.getenv("MT5_API_URL")
                or "http://mt5:5001"
            )
            eq = None
            try:
                r = requests.get(f"{str(mt5_base).rstrip('/')}/account_info", timeout=1.5)
                if r.ok:
                    ai = r.json() or {}
                    if isinstance(ai, list) and ai:
                        ai = ai[0]
                    if isinstance(ai, dict):
                        eq = float(ai.get('equity') or ai.get('Equity') or 0) or None
            except Exception:
                eq = None
            # Load risk policy for daily % caps
            try:
                pol = load_policies() or {}
                risk_pol = pol.get('risk', {}) if isinstance(pol, dict) else {}
                profit_pct = float(risk_pol.get('daily_profit_target_pct', 1.0))
                loss_pct = float(risk_pol.get('max_daily_loss_pct', 3.0))
            except Exception:
                profit_pct, loss_pct = 1.0, 3.0
            target_amt = (eq or 0) * (profit_pct / 100.0)
            loss_amt = (eq or 0) * (loss_pct / 100.0)
            pnl_norm = None
            if pnl_today >= 0 and target_amt > 0:
                pnl_norm = min(1.0, pnl_today / target_amt)
            elif pnl_today < 0 and loss_amt > 0:
                pnl_norm = -min(1.0, abs(pnl_today) / loss_amt)
            payload["pnl_norm"] = pnl_norm
            payload["pnl_today"] = pnl_today
        except Exception:
            pass

        return Response(payload)


class MarketMiniView(views.APIView):
    """Slim market header payload: VIX/DXY sparklines + next news.

    Tries DB Bar data for symbols 'VIX' and 'DXY' (any timeframe) and falls back to Redis keys:
      - market:vix:series, market:dxy:series (JSON lists)
      - market:news:next (JSON {label, ts})
    """
    permission_classes = [AllowAny]

    def get(self, request):
        def bar_series(symbol: str, limit: int = 40):
            try:
                qs = Bar.objects.filter(symbol=symbol).order_by('-time')[:limit]
                if qs:
                    vals = [float(b.close or 0) for b in reversed(list(qs))]
                    return vals, (vals[-1] if vals else None)
            except Exception:
                pass
            return None, None

        vix_series, vix_last = bar_series('VIX', 40)
        dxy_series, dxy_last = bar_series('DXY', 40)

        # Fallback to Redis cached lists if bars missing
        if (vix_series is None or not vix_series) and _redis_client() is not None:
            try:
                r = _redis_client()
                raw = r.get('market:vix:series')
                if raw:
                    import json as _json
                    vix_series = _json.loads(raw)
                    vix_last = vix_series[-1] if vix_series else None
            except Exception:
                pass
        if (dxy_series is None or not dxy_series) and _redis_client() is not None:
            try:
                r = _redis_client()
                raw = r.get('market:dxy:series')
                if raw:
                    import json as _json
                    dxy_series = _json.loads(raw)
                    dxy_last = dxy_series[-1] if dxy_series else None
            except Exception:
                pass

        # Next news (optional): read from Redis market:news:next {label, ts}
        news = {"label": None, "countdown": None}
        try:
            r = _redis_client()
            if r is not None:
                raw = r.get('market:news:next')
                if raw:
                    import json as _json
                    obj = _json.loads(raw)
                    lbl = obj.get('label')
                    ts = obj.get('ts')
                    if ts:
                        from django.utils import timezone
                        try:
                            when = timezone.datetime.fromisoformat(ts.replace('Z','+00:00'))
                        except Exception:
                            when = None
                        if when is not None:
                            delta = when - timezone.now()
                            secs = int(delta.total_seconds())
                            if secs > 0:
                                m, s = divmod(secs, 60)
                                h, m = divmod(m, 60)
                                news['countdown'] = f"in {h}h {m}m"
                    news['label'] = lbl
        except Exception:
            pass

        # Simple regime heuristic from last two points (if available)
        regime = None
        try:
            def trend(arr):
                if not arr or len(arr) < 2:
                    return 0
                return (arr[-1] - arr[0]) / (abs(arr[0]) + 1e-6)
            vix_tr = trend(vix_series)
            dxy_tr = trend(dxy_series)
            if vix_tr > 0.02 or dxy_tr > 0.01:
                regime = "Risk-Off / Choppy"
            elif vix_tr < -0.02 and dxy_tr < 0.0:
                regime = "Risk-On / Trending"
            else:
                regime = "Neutral"
        except Exception:
            regime = None

        payload = {
            'vix': {'series': vix_series or [], 'value': vix_last},
            'dxy': {'series': dxy_series or [], 'value': dxy_last},
            'news': news,
            'regime': regime,
        }
        return Response(payload)


class MarketFetchView(views.APIView):
    """Fetch VIX/DXY from public APIs and cache to Redis (TTL).

    Tries Yahoo Finance chart API (no key) for ^VIX and ^DXY 1d/5m.
    Use responsibly; add outbound allowances in your environment.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        import requests as _req
        rcli = _redis_client()
        out = {}

        def fetch_yahoo(ticker: str):
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=5m&range=1d"
            try:
                resp = _req.get(url, timeout=3)
                if resp.ok:
                    data = resp.json()
                    closes = (
                        data.get('chart', {})
                        .get('result', [{}])[0]
                        .get('indicators', {})
                        .get('quote', [{}])[0]
                        .get('close', [])
                    )
                    series = [float(x) for x in closes if x is not None]
                    return series
            except Exception:
                return []
            return []

        vix_series = fetch_yahoo('%5EVIX')
        dxy_series = fetch_yahoo('%5EDXY')
        out['vix'] = len(vix_series)
        out['dxy'] = len(dxy_series)
        if rcli is not None:
            try:
                if vix_series:
                    rcli.setex('market:vix:series', 300, _json.dumps(vix_series))
                if dxy_series:
                    rcli.setex('market:dxy:series', 300, _json.dumps(dxy_series))
            except Exception:
                pass
        return Response({'ok': True, **out})


class MarketNewsPublisherView(views.APIView):
    """Publish next high-impact news item into Redis for header consumption.

    POST JSON: { label: str, ts: ISO8601 }  (ts optional)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data or {}
        except Exception:
            try:
                data = _json.loads(request.body or b"{}")
            except Exception:
                data = {}
        lbl = data.get('label')
        ts = data.get('ts')
        if not lbl:
            return Response({'ok': False, 'error': 'label required'}, status=400)
        r = _redis_client()
        if r is None:
            return Response({'ok': False, 'error': 'redis unavailable'}, status=503)
        try:
            r.setex('market:news:next', 3600, _json.dumps({'label': lbl, 'ts': ts}))
            return Response({'ok': True})
        except Exception as e:
            return Response({'ok': False, 'error': str(e)}, status=500)


class PositionsProxyView(views.APIView):
    """Proxy positions from MT5 bridge with normalization and safe fallback.

    GET /api/v1/account/positions -> [] on failure.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        base = (
            os.getenv("MT5_URL")
            or os.getenv("MT5_API_URL")
            or "http://mt5:5001"
        )
        try:
            r = requests.get(f"{str(base).rstrip('/')}/positions_get", timeout=2.5)
            if not r.ok:
                return Response([], status=200)
            data = r.json() or []
            if not isinstance(data, list):
                return Response([], status=200)
            # Normalize time fields to ISO strings (if present)
            out = []
            for p in data:
                if not isinstance(p, dict):
                    continue
                q = dict(p)
                for tkey in ("time", "time_update"):
                    if tkey in q and q[tkey] is not None:
                        try:
                            # try milliseconds → ISO
                            import pandas as _pd
                            q[tkey] = _pd.to_datetime(int(q[tkey]), unit='s', errors='coerce').isoformat()
                        except Exception:
                            pass
                out.append(q)
            return Response(out)
        except Exception:
            return Response([], status=200)


class AccountInfoView(views.APIView):
    """Return normalized MT5 account info with stable lowercase keys.

    GET /api/v1/account/info -> { equity, balance, margin, free_margin, margin_level, profit, login, server, currency }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        base = (
            os.getenv("MT5_URL")
            or os.getenv("MT5_API_URL")
            or "http://mt5:5001"
        )
        try:
            r = requests.get(f"{str(base).rstrip('/')}/account_info", timeout=2.5)
            if not r.ok:
                return Response({}, status=200)
            data = r.json() or {}
            if isinstance(data, list) and data:
                data = data[0]
            if not isinstance(data, dict):
                return Response({}, status=200)
            # normalize keys to lowercase
            norm = {str(k).lower(): v for k, v in data.items()}
            # keep only common fields
            keep = [
                'equity','balance','margin','free_margin','margin_level','profit','login','server','currency'
            ]
            out = {k: norm.get(k) for k in keep}
            return Response(out)
        except Exception:
            return Response({}, status=200)


class JournalAppendView(views.APIView):
    """Append a journal entry; optionally linked to a trade by id.

    POST JSON: { trade_id?, kind?, text?, tags?, meta? }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        trade_id = data.get('trade_id')
        kind = data.get('kind') or 'note'
        text = data.get('text') or ''
        tags = data.get('tags') or []
        meta = data.get('meta') or {}
        try:
            je = None
            if trade_id:
                try:
                    trade = Trade.objects.get(id=trade_id)
                except Trade.DoesNotExist:
                    return Response({'error': 'Trade not found'}, status=404)
                # Upsert against OneToOne
                je, _ = JournalEntry.objects.get_or_create(trade=trade)
            else:
                # Create a detached JournalEntry requires a trade; if no trade, emulate minimal store via meta
                return Response({'error': 'trade_id required for now'}, status=400)
            # Store text in notes; stash kind/tags/meta as JSON in notes if provided
            payload = { 'kind': kind, 'text': text, 'tags': tags, 'meta': meta }
            existing = je.notes or ''
            sep = '\n---\n' if existing else ''
            import json as _json
            je.notes = f"{existing}{sep}{_json.dumps(payload)}"
            je.save()
            return Response({'ok': True, 'id': je.id, 'ts': je.updated_at.isoformat()})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class JournalRecentView(views.APIView):
    """Return recent journal entries (last N)."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            limit = int(request.GET.get('limit', '50'))
        except Exception:
            limit = 50
        qs = JournalEntry.objects.select_related('trade').order_by('-updated_at')[:max(1, min(200, limit))]
        out = []
        for je in qs:
            out.append({
                'id': je.id,
                'ts': je.updated_at.isoformat(),
                'trade_id': je.trade_id,
                'text': je.notes or '',
            })
        return Response(out)


class AccountRiskView(views.APIView):
    """Compute session risk envelope using SoD equity and policy percentages.

    Policy is loaded from app.utils.policies (daily_profit_target_pct, max_daily_loss_pct).
    SoD equity is derived from account info and stored per-day in Redis as sod_equity:YYYYMMDD.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        now = timezone.now()
        # Trading-day anchor (e.g., 23:00 Europe/London)
        anchor_utc = _trading_day_start_utc(now)
        tz_name = os.getenv("TRADING_DAY_TZ", "Europe/London")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")
        # Date keys are based on local trading day (anchor date)
        anchor_local = anchor_utc.astimezone(tz)
        today_key = anchor_local.strftime('%Y%m%d')
        yesterday_key = (anchor_local - timedelta(days=1)).strftime('%Y%m%d')
        r = _redis_client()
        # Resolve equity via account_info
        equity = None
        try:
            base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
            rq = requests.get(f"{str(base).rstrip('/')}/account_info", timeout=1.5)
            if rq.ok:
                data = rq.json() or {}
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    equity = float(data.get('equity') or data.get('Equity') or 0)
        except Exception:
            pass
        # SoD equity: cached per trading day (local) with manual override support
        sod_equity = None
        if r is not None:
            try:
                # 1) Manual override for this trading day
                raw_ovr = r.get(f"sod_equity_override:{today_key}")
                if raw_ovr:
                    sod_equity = float(raw_ovr)
                # 2) Stored snapshot
                if sod_equity is None:
                    raw = r.get(f"sod_equity:{today_key}")
                    if raw:
                        sod_equity = float(raw)
            except Exception:
                sod_equity = None
        # Optional environment override (useful for demos)
        if sod_equity is None:
            try:
                env_override = os.getenv('SOD_EQUITY_OVERRIDE')
                if env_override:
                    sod_equity = float(env_override)
            except Exception:
                pass

        # Compute session bounds (current and previous)
        start_utc, end_utc, _tk = session_bounds(now)
        y_start_utc, y_end_utc, _yk = session_bounds(start_utc - timedelta(seconds=1))

        # If SoD still missing, derive from previous session close (SoD_yesterday + PnL_yesterday)
        prev_close_equity = None
        if sod_equity is None:
            try:
                sod_y = None
                if r is not None:
                    rawy = r.get(f"sod_equity_override:{yesterday_key}") or r.get(f"sod_equity:{yesterday_key}")
                    if rawy:
                        sod_y = float(rawy)
                pnl_y = float(sum([
                    (t.pnl or 0.0)
                    for t in Trade.objects.filter(
                        close_time__gte=y_start_utc,
                        close_time__lt=y_end_utc,
                        close_time__isnull=False
                    )
                ]))
                if sod_y is not None:
                    prev_close_equity = sod_y + pnl_y
                    sod_equity = prev_close_equity
                    if r is not None:
                        try:
                            r.setex(f"sod_equity:{today_key}", 72*3600, str(sod_equity))
                        except Exception:
                            pass
            except Exception:
                pass
        # As a final fallback: snapshot current equity once past anchor
        if sod_equity is None and equity is not None and r is not None and now >= anchor_utc:
            try:
                r.setex(f"sod_equity:{today_key}", 72*3600, str(equity))
                sod_equity = equity
            except Exception:
                sod_equity = equity
        # Previous close equity (prefer computed from previous session; else stored snapshot)
        if prev_close_equity is None and r is not None:
            try:
                rawp = r.get(f"sod_equity_override:{yesterday_key}") or r.get(f"sod_equity:{yesterday_key}")
                if rawp:
                    # If stored yesterday SoD; add pnl_y to estimate close
                    pnl_y = float(sum([
                        (t.pnl or 0.0)
                        for t in Trade.objects.filter(
                            close_time__gte=y_start_utc,
                            close_time__lt=y_end_utc,
                            close_time__isnull=False
                        )
                    ]))
                    prev_close_equity = float(rawp) + pnl_y
            except Exception:
                prev_close_equity = None

        # Policy
        pol = load_policies() or {}
        risk_pol = pol.get('risk', {}) if isinstance(pol, dict) else {}
        daily_profit_pct = float(risk_pol.get('daily_profit_target_pct', 1.0))
        daily_risk_pct = float(risk_pol.get('max_daily_loss_pct', 3.0))
        target_amount = (sod_equity or 0) * (daily_profit_pct / 100.0)
        loss_amount = (sod_equity or 0) * (daily_risk_pct / 100.0)
        used_pct = None
        # Compute exposure from open positions: sum(|volume * price_current|)/equity
        exposure_pct = None
        try:
            if equity is not None and sod_equity and loss_amount > 0:
                if equity < sod_equity:
                    used_pct = max(0.0, min(1.0, (sod_equity - equity) / loss_amount)) * 100.0
                elif target_amount > 0:
                    used_pct = max(0.0, min(1.0, (equity - sod_equity) / target_amount)) * 100.0
        except Exception:
            used_pct = None
        # Exposure computation
        try:
            if equity and equity > 0:
                base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
                rp = requests.get(f"{str(base).rstrip('/')}/positions_get", timeout=2.5)
                if rp.ok:
                    arr = rp.json() or []
                    total_notional = 0.0
                    if isinstance(arr, list):
                        for p in arr:
                            try:
                                vol = float(p.get('volume') or 0)
                                price = float(p.get('price_current') or p.get('price_open') or 0)
                                total_notional += abs(vol * price)
                            except Exception:
                                continue
                    exposure_pct = (total_notional / equity) if equity else None
        except Exception:
            exposure_pct = None

        return Response({
            'sod_equity': sod_equity,
            'prev_close_equity': prev_close_equity,
            'daily_profit_pct': daily_profit_pct,
            'daily_risk_pct': daily_risk_pct,
            'target_amount': target_amount,
            'loss_amount': loss_amount,
            'used_pct': used_pct,
            'exposure_pct': exposure_pct,
        })


class AccountSoDView(views.APIView):
    """Return Start-of-Day equity snapshot for a given date (YYYY-MM-DD).

    Query: date=YYYY-MM-DD (optional; default today)
    Response: { date: 'YYYY-MM-DD', sod_equity: number | null, source: 'redis'|'fallback' }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        import datetime as _dt
        q = request.GET.get('date')
        try:
            if q:
                dt = _dt.datetime.fromisoformat(q)
                date_key = dt.strftime('%Y%m%d')
                date_out = dt.strftime('%Y-%m-%d')
            else:
                d = timezone.now().date()
                date_key = d.strftime('%Y%m%d')
                date_out = d.strftime('%Y-%m-%d')
        except Exception:
            d = timezone.now().date()
            date_key = d.strftime('%Y%m%d')
            date_out = d.strftime('%Y-%m-%d')
        key = f"sod_equity:{date_key}"
        r = _redis_client()
        val = None
        source = None
        if r is not None:
            try:
                raw = r.get(key)
                if raw:
                    val = float(raw)
                    source = 'redis'
            except Exception:
                val = None
        # Optional fallback: if not found and MT5 reachable, return current equity
        if val is None:
            try:
                base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
                rq = requests.get(f"{str(base).rstrip('/')}/account_info", timeout=1.5)
                if rq.ok:
                    data = rq.json() or {}
                    if isinstance(data, list) and data:
                        data = data[0]
                    val = float(data.get('equity') or data.get('Equity') or 0)
                    source = 'fallback'
            except Exception:
                val = None
        return Response({
            'date': date_out,
            'sod_equity': val,
            'source': source,
        })

    def post(self, request):
        """Manually override or clear SoD equity for a given date.

        Body JSON: { sod_equity?: number, date?: 'YYYY-MM-DD', clear?: bool }
        When clear=true, removes the override for that date.
        Stores under Redis key sod_equity_override:YYYYMMDD
        """
        r = _redis_client()
        if r is None:
            return Response({'error': 'redis unavailable'}, status=503)
        data = request.data or {}
        from django.utils import timezone
        import datetime as _dt
        q = data.get('date')
        try:
            if q:
                dt = _dt.datetime.fromisoformat(q)
            else:
                dt = timezone.now()
            date_key = dt.strftime('%Y%m%d')
        except Exception:
            dt = timezone.now()
            date_key = dt.strftime('%Y%m%d')
        key = f"sod_equity_override:{date_key}"
        if data.get('clear'):
            try:
                r.delete(key)
            except Exception:
                pass
            return Response({'ok': True, 'cleared': True, 'date': dt.strftime('%Y-%m-%d')})
        val = data.get('sod_equity')
        try:
            sval = str(float(val))
        except Exception:
            return Response({'error': 'sod_equity must be numeric'}, status=400)
        try:
            r.set(key, sval)
            return Response({'ok': True, 'date': dt.strftime('%Y-%m-%d'), 'sod_equity': float(sval)})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class OrderMarketProxyView(views.APIView):
    """Place a market order via local order helper (safe proxy)."""
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        symbol = data.get('symbol')
        volume = data.get('volume')
        side = (data.get('side') or '').lower()
        if not symbol or volume is None or side not in ('buy','sell'):
            return Response({'error': 'symbol, volume, side required'}, status=400)
        order_type = 'BUY' if side == 'buy' else 'SELL'
        sl = data.get('sl', 0.0)
        tp = data.get('tp', 0.0)
        comment = data.get('comment', '')
        # Delegate to existing helper
        try:
            resp = send_market_order(symbol=symbol, volume=volume, order_type=order_type, sl=sl, tp=tp, deviation=20, comment=comment, magic=0, type_filling='2')
            ok = bool(resp)
            return Response({'ok': ok, 'order': resp})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class OrderModifyProxyView(views.APIView):
    """Modify SL/TP for an existing position.

    Note: underlying modify helper expects trade id and ticket; if id is unknown, this may not persist a mutation record.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        ticket = data.get('ticket')
        if ticket is None:
            return Response({'error': 'ticket required'}, status=400)
        sl = data.get('sl')
        tp = data.get('tp')
        # Best-effort: call bridge partial modify is not available; use helper if possible
        try:
            ok, data = modify_sl_tp_ticket(int(ticket), sl=sl, tp=tp)
            return Response({'ok': ok, 'result': data}, status=200 if ok else 400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class OrderCloseProxyView(views.APIView):
    """Close full or partial position via MT5 bridge partial_close endpoint."""
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        try:
            ticket = int(data.get('ticket'))
        except Exception:
            return Response({'error': 'ticket required'}, status=400)
        fraction = data.get('fraction')
        volume = data.get('volume')
        try:
            base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
            base = str(base).rstrip('/')

            # Helper to fetch position details (for full close or fallbacks)
            def _fetch_position(tkt: int):
                try:
                    rp = requests.get(f"{base}/positions_get", timeout=2.5)
                    if not rp.ok:
                        return None
                    arr = rp.json() or []
                    for p in arr:
                        try:
                            if int(p.get('ticket') or p.get('Ticket') or -1) == int(tkt):
                                return p
                        except Exception:
                            continue
                except Exception:
                    return None
                return None

            # Prefer explicit volume if provided; else fraction; if neither provided, attempt full close by resolving volume from bridge
            payload = {'ticket': ticket}
            if volume is not None:
                try:
                    payload['volume'] = float(volume)
                except Exception:
                    return Response({'error': 'volume must be numeric'}, status=400)
            elif fraction is not None:
                try:
                    payload['fraction'] = float(fraction)
                except Exception:
                    return Response({'error': 'fraction must be numeric'}, status=400)
            else:
                # Full close intent: resolve current volume from bridge
                pos = _fetch_position(ticket)
                if pos and pos.get('volume') is not None:
                    try:
                        payload['volume'] = float(pos.get('volume'))
                    except Exception:
                        # Fall back to fraction when volume parse fails
                        payload['fraction'] = 0.99  # close nearly full if exact volume unavailable
                else:
                    # If we cannot resolve position, proceed with v2 and let bridge respond; we'll retry/fallback below
                    payload['fraction'] = 0.99

            # Attempt with retry/backoff on transient HTTP issues or 404s
            last_resp = None
            for attempt in range(3):
                r = requests.post(f"{base}/partial_close_v2", json=payload, timeout=6.0)
                last_resp = r
                if r.ok:
                    try:
                        body = r.json()
                        return Response(body if isinstance(body, dict) else {'ok': True})
                    except Exception:
                        return Response({'ok': True})
                if r.status_code in (404, 502, 503, 504):
                    # Small backoff then retry
                    import time as _t
                    _t.sleep(0.35 * (attempt + 1))
                    continue
                # Other statuses: break and handle below
                break

            # If v2 failed, try fallback endpoints
            # 1) Legacy partial_close if available (requires symbol + fraction)
            pos = _fetch_position(ticket)
            if pos:
                try:
                    symbol = str(pos.get('symbol') or pos.get('Symbol'))
                    frac = None
                    if 'fraction' in payload:
                        frac = float(payload['fraction'])
                    elif 'volume' in payload:
                        try:
                            v_req = float(payload['volume'])
                            v_pos = float(pos.get('volume') or pos.get('Volume') or 0.0)
                            if v_pos > 0:
                                frac = max(0.01, min(0.99, v_req / v_pos))
                        except Exception:
                            frac = None
                    if frac is None:
                        frac = 0.99
                    rl = requests.post(f"{base}/partial_close", json={'ticket': int(ticket), 'symbol': symbol, 'fraction': float(frac)}, timeout=6.0)
                    if rl.ok:
                        body = rl.json() if rl.headers.get('content-type','').startswith('application/json') else {'ok': True}
                        return Response({'ok': True, 'result': body})
                except Exception:
                    pass

            # 2) If we can fetch the position, try legacy full-close endpoint which requires full position data
            if pos:
                try:
                    position_payload = {
                        'type': int(pos.get('type') or pos.get('Type') or 0),
                        'ticket': int(pos.get('ticket') or pos.get('Ticket') or ticket),
                        'symbol': str(pos.get('symbol') or pos.get('Symbol')),
                        'volume': float(pos.get('volume') or pos.get('Volume') or 0.0),
                    }
                    rc = requests.post(f"{base}/close_position", json={'position': position_payload}, timeout=6.0)
                    if rc.ok:
                        body = rc.json() if rc.headers.get('content-type','').startswith('application/json') else {'ok': True}
                        return Response({'ok': True, 'result': body})
                except Exception:
                    pass

            # 3) As a last check, if position is no longer present, treat as already closed
            if not pos:
                pos2 = _fetch_position(ticket)
                if not pos2:
                    return Response({'ok': True, 'note': 'position_not_found_after_retry_maybe_closed'})

            # All attempts failed; return bridge error details when available
            if last_resp is not None:
                detail = None
                try:
                    detail = last_resp.json()
                except Exception:
                    detail = {'text': getattr(last_resp, 'text', '')}
                return Response({'error': 'bridge_http', 'status': last_resp.status_code, 'detail': detail}, status=502)
            return Response({'error': 'bridge_http', 'status': None}, status=502)
        except Exception as e:
            return Response({'error': str(e)}, status=502)


class DisciplineEventsView(views.APIView):
    """GET discipline ledger for a date from Redis events:discipline:YYYYMMDD."""
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        day = request.GET.get('date') or timezone.now().strftime('%Y-%m-%d')
        key = f"events:discipline:{day.replace('-','')}"
        r = _redis_client()
        out = []
        if r is not None:
            try:
                items = r.lrange(key, 0, -1) or []
                for b in items:
                    try:
                        out.append(json.loads(b))
                    except Exception:
                        continue
            except Exception:
                out = []
        return Response(out)


class BehaviorEventsTodayView(views.APIView):
    """Return today's behavior events as [{ts, type, weight, explain}]."""
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        day = timezone.now().strftime('%Y-%m-%d')
        key = f"events:discipline:{day.replace('-', '')}"
        r = _redis_client()
        items = []
        if r is not None:
            try:
                raw = r.lrange(key, 0, -1) or []
                for b in raw:
                    try:
                        e = json.loads(b)
                        items.append({
                            'ts': e.get('ts'),
                            'type': e.get('kind'),
                            'weight': e.get('delta'),
                            'explain': e.get('note') or None,
                        })
                    except Exception:
                        continue
            except Exception:
                items = []
        return Response(items)


class DisciplineEventAppendView(views.APIView):
    """POST append a discipline ledger event."""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.utils import timezone
        data = request.data or {}
        kind = data.get('kind')
        delta = data.get('delta')
        ts = data.get('ts')
        if kind is None or delta is None:
            return Response({'error': 'kind and delta required'}, status=400)
        day = timezone.now().strftime('%Y-%m-%d')
        key = f"events:discipline:{day.replace('-','')}"
        r = _redis_client()
        if r is None:
            return Response({'error': 'redis unavailable'}, status=503)
        try:
            evt = {'ts': ts or timezone.now().isoformat(), 'kind': str(kind), 'delta': int(delta)}
            r.rpush(key, json.dumps(evt))
            return Response({'ok': True})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class MarketSymbolsView(views.APIView):
    """Return a list of available symbols (Bars or Trades)."""
    permission_classes = [AllowAny]

    def get(self, request):
        syms = []
        try:
            syms = list(Bar.objects.values_list('symbol', flat=True).distinct().order_by('symbol'))
            if not syms:
                syms = list(Trade.objects.values_list('symbol', flat=True).distinct().order_by('symbol'))
        except Exception:
            syms = []
        return Response({'symbols': syms})


class MarketCalendarNextView(views.APIView):
    """Return next high-impact events from Redis list market:calendar:next."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            limit = int(request.GET.get('limit', '5'))
        except Exception:
            limit = 5
        r = _redis_client()
        out = []
        if r is not None:
            try:
                items = r.lrange('market:calendar:next', 0, limit-1) or []
                for b in items:
                    try:
                        out.append(json.loads(b))
                    except Exception:
                        continue
            except Exception:
                out = []
        return Response(out)


class MarketRegimeView(views.APIView):
    """Return regime and feature set derived from cached series."""
    permission_classes = [AllowAny]

    def get(self, request):
        r = _redis_client()
        def load_series(key):
            if r is None:
                return []
            try:
                raw = r.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:
                return []
            return []
        vix = load_series('market:vix:series')
        dxy = load_series('market:dxy:series')
        def trend(arr):
            if not arr or len(arr) < 2:
                return 0.0
            try:
                return (float(arr[-1]) - float(arr[0])) / (abs(float(arr[0])) + 1e-6)
            except Exception:
                return 0.0
        vtr = trend(vix)
        dtr = trend(dxy)
        regime = 'Neutral'
        if vtr > 0.02 or dtr > 0.01:
            regime = 'Risk-Off / Choppy'
        elif vtr < -0.02 and dtr < 0.0:
            regime = 'Risk-On / Trending'
        return Response({'regime': regime, 'score': None, 'features': {'vix_trend': vtr, 'dxy_trend': dtr}})


class FeedsStreamView(views.APIView):
    """Server-Sent Events stream for live feeds and whispers.

    Query param `topics` is a comma-separated list of: mirror, whispers, market.
    Emits events:
      - event: mirror, data: {...}
      - event: whisper, data: {...}
      - event: market, data: {...}
      - event: heartbeat every 30s
    """
    permission_classes = [AllowAny]

    def get(self, request):
        topics = (request.GET.get('topics') or 'mirror,whispers,market').split(',')
        topics = [t.strip() for t in topics if t.strip()]
        channels = []
        if 'whispers' in topics:
            channels.append('pulse.whispers')
        if 'market' in topics:
            channels.append('pulse.feeds')
        if 'mirror' in topics and 'pulse.feeds' not in channels:
            channels.append('pulse.feeds')

        r = _redis_client()
        if r is None:
            return StreamingHttpResponse((chunk for chunk in ["event: error\n", "data: \"redis unavailable\"\n\n"]), content_type='text/event-stream')

        pubsub = r.pubsub()
        try:
            for ch in channels:
                pubsub.subscribe(ch)
        except Exception:
            pass

        def _stream():
            import time as _t
            last_hb = _t.time()
            yield b"event: hello\n"
            yield f"data: {{\"ok\":true,\"topics\":{json.dumps(topics)} }}\n\n".encode()
            while True:
                try:
                    msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    now = _t.time()
                    if msg and msg.get('type') == 'message':
                        ch = msg.get('channel') or msg.get('pattern')
                        try:
                            data = msg.get('data')
                            if isinstance(data, bytes):
                                data = data.decode('utf-8', 'ignore')
                        except Exception:
                            data = '{}'
                        ev = 'market' if ch == 'pulse.feeds' else 'whisper'
                        yield f"event: {ev}\n".encode()
                        yield f"data: {data}\n\n".encode()
                    if now - last_hb >= 30:
                        yield b"event: heartbeat\n"
                        yield b"data: \"\"\n\n"
                        last_hb = now
                except GeneratorExit:
                    break
                except Exception:
                    _t.sleep(0.5)
        resp = StreamingHttpResponse(_stream(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


class BehavioralPatternsView(views.APIView):
    """Analyze recent behavioral patterns from Trades and journal signals.

    Returns a coarse summary for last 30 days and current active flags.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        now = timezone.now()
        since = now - timezone.timedelta(days=30)
        patterns = {
            'window_days': 30,
            'revenge_trading': {'active': False, 'count': 0, 'note': ''},
            'fomo': {'active': False, 'count': 0, 'note': ''},
            'fear_cut_winners': {'active': False, 'count': 0, 'note': ''},
        }
        try:
            # Load recent closed trades
            qs = Trade.objects.filter(close_time__gte=since).order_by('entry_time')
            trades = list(qs)
            # Revenge: sequences of >=2 losses with quick re-entry (< 10 min)
            rev = 0
            for i in range(1, len(trades)):
                prev = trades[i-1]
                cur = trades[i]
                try:
                    prev_loss = (prev.pnl or 0) < 0
                    gap_min = (cur.entry_time - prev.close_time).total_seconds() / 60.0 if (cur.entry_time and prev.close_time) else 999
                    if prev_loss and gap_min <= 10:
                        rev += 1
                except Exception:
                    continue
            patterns['revenge_trading']['count'] = rev
            patterns['revenge_trading']['active'] = rev >= 1
            if rev:
                patterns['revenge_trading']['note'] = f"{rev} quick re-entries after losses"
            # FOMO: very short inter-trade intervals overall (p25 < 5 min)
            gaps = []
            for i in range(1, len(trades)):
                try:
                    gaps.append((trades[i].entry_time - trades[i-1].entry_time).total_seconds() / 60.0)
                except Exception:
                    continue
            if gaps:
                gsorted = sorted(gaps)
                p25 = gsorted[max(0, int(0.25*(len(gsorted)-1)))]
                patterns['fomo']['active'] = p25 < 5.0
                patterns['fomo']['count'] = sum(1 for g in gaps if g < 5.0)
                patterns['fomo']['note'] = f"p25 gap {p25:.1f}m"
            # Fear of letting winners run: avg efficiency < 50%
            effs = []
            for t in trades:
                try:
                    pnl = float(t.pnl or 0)
                    peak = float(t.max_profit or 0)
                    if peak > 0 and pnl > 0:
                        effs.append(max(0.0, min(1.0, pnl/peak)))
                except Exception:
                    continue
            if effs:
                avg = sum(effs)/len(effs)
                patterns['fear_cut_winners']['active'] = avg < 0.5
                patterns['fear_cut_winners']['count'] = len([e for e in effs if e < 0.5])
                patterns['fear_cut_winners']['note'] = f"avg eff {avg*100:.0f}%"
        except Exception:
            pass
        # Publish lightweight Whisperer nudges when patterns activate (deduped)
        try:
            import time as _t
            from pulse.rt import publish_whisper, seen_once
            def _whisper(payload: dict, key: str, ttl: int = 300):
                try:
                    if seen_once(f"nudge:{key}", ttl_seconds=ttl):
                        publish_whisper(payload)
                except Exception:
                    pass
            now = _t.time()
            # Revenge trading nudge
            rv = patterns.get('revenge_trading') or {}
            if rv.get('active'):
                _whisper({
                    'id': f'pat-revenge-{int(now)}',
                    'ts': now,
                    'category': 'patience',
                    'severity': 'warn',
                    'message': 'Quick re-entries after losses detected. Take a 10–15m reset?',
                    'reasons': [
                        {'key': 'revenge_count', 'value': int(rv.get('count') or 0)},
                        {'key': 'note', 'value': rv.get('note') or ''},
                    ],
                    'actions': [{'label': 'Start 15-min timer', 'action': 'act_start_timer_15'}],
                    'ttl_seconds': 600,
                    'cooldown_key': 'pattern_revenge',
                    'cooldown_seconds': 300,
                    'channel': ['dashboard']
                }, key='pattern:revenge')
            # FOMO tempo nudge
            fo = patterns.get('fomo') or {}
            if fo.get('active'):
                _whisper({
                    'id': f'pat-fomo-{int(now)}',
                    'ts': now,
                    'category': 'patience',
                    'severity': 'suggest',
                    'message': 'Tempo rising (short inter-trade gaps). Slow spacing and wait for A+ setup.',
                    'reasons': [
                        {'key': 'fomo_count', 'value': int(fo.get('count') or 0)},
                        {'key': 'note', 'value': fo.get('note') or ''},
                    ],
                    'actions': [{'label': 'Size down next entry', 'action': 'act_size_down'}],
                    'ttl_seconds': 600,
                    'cooldown_key': 'pattern_fomo',
                    'cooldown_seconds': 300,
                    'channel': ['dashboard']
                }, key='pattern:fomo')
            # Fear of cutting winners nudge
            fw = patterns.get('fear_cut_winners') or {}
            if fw.get('active'):
                _whisper({
                    'id': f'pat-fearcut-{int(now)}',
                    'ts': now,
                    'category': 'profit',
                    'severity': 'suggest',
                    'message': 'Profit efficiency low. Consider partials and a trailing stop to let winners run.',
                    'reasons': [
                        {'key': 'fear_count', 'value': int(fw.get('count') or 0)},
                        {'key': 'note', 'value': fw.get('note') or ''},
                    ],
                    'actions': [{'label': 'Trail 50%', 'action': 'act_trail_50'}],
                    'ttl_seconds': 600,
                    'cooldown_key': 'pattern_fear',
                    'cooldown_seconds': 300,
                    'channel': ['dashboard']
                }, key='pattern:fear_cut_winners')
        except Exception:
            pass
        return Response(patterns)


class JournalEntryPostView(views.APIView):
    """Structured journal entry for post-trade reflection.

    POST JSON: { trade_id, confidence?, reflection?, text?, tags? }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        trade_id = data.get('trade_id')
        if not trade_id:
            return Response({'error': 'trade_id required'}, status=400)
        try:
            trade = Trade.objects.get(id=trade_id)
        except Trade.DoesNotExist:
            return Response({'error': 'Trade not found'}, status=404)
        conf = data.get('confidence')
        refl = data.get('reflection') or ''
        notes = data.get('text') or ''
        tags = data.get('tags') or []
        je, _ = JournalEntry.objects.get_or_create(trade=trade)
        if conf is not None:
            try:
                je.pre_trade_confidence = int(conf)
            except Exception:
                pass
        if refl:
            je.post_trade_feeling = (je.post_trade_feeling or '') + (('\n' if je.post_trade_feeling else '') + refl)
        if notes:
            je.notes = (je.notes or '') + (('\n' if je.notes else '') + notes)
        je.save()
        return Response({'ok': True, 'id': je.id, 'ts': je.updated_at.isoformat()})


class SessionSetFocusView(views.APIView):
    """Set daily psychological focus in Redis (per-day)."""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.utils import timezone
        focus = (request.data or {}).get('focus')
        if not focus:
            return Response({'error': 'focus required'}, status=400)
        today = timezone.now().strftime('%Y%m%d')
        r = _redis_client()
        if r is None:
            return Response({'error': 'redis unavailable'}, status=503)
        try:
            r.setex(f"session:focus:{today}", 48*3600, str(focus))
            return Response({'ok': True, 'focus': focus})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class PositionProtectOptionsView(views.APIView):
    """Suggest protection options for an open position (ticket).

    Returns a list of actions with labels and suggested params; no execution.
    """
    permission_classes = [AllowAny]

    def get(self, request, ticket: int):
        base = os.getenv("MT5_URL") or os.getenv("MT5_API_URL") or "http://mt5:5001"
        try:
            r = requests.get(f"{str(base).rstrip('/')}/positions_get", timeout=2.5)
            if not r.ok:
                return Response({'actions': []})
            data = r.json() or []
            ps = [p for p in data if int(p.get('ticket', -1)) == int(ticket)] if isinstance(data, list) else []
            if not ps:
                return Response({'actions': []})
            p = ps[0]
            sym = p.get('symbol')
            typ = 'BUY' if int(p.get('type', 0)) == 0 else 'SELL'
            po = float(p.get('price_open') or 0)
            pc = float(p.get('price_current') or 0)
            profit = float(p.get('profit') or 0)
            # Propose options
            actions = []
            # Breakeven
            actions.append({'label': 'Move SL to BE', 'action': 'protect_breakeven', 'params': {'ticket': ticket, 'symbol': sym}})
            # Trail 50% of current profit (naive, price-space lock)
            if profit > 0:
                # Approximate lock price half-way from entry to current favorable
                if typ == 'BUY':
                    lock = po + 0.5 * (pc - po)
                else:
                    lock = po - 0.5 * (po - pc)
                actions.append({'label': 'Trail 50%', 'action': 'protect_trail_50', 'params': {'ticket': ticket, 'symbol': sym, 'lock_ratio': 0.5, 'suggested_sl': round(lock, 5)}})
                actions.append({'label': 'Partial 25%', 'action': 'partial_close_25', 'params': {'ticket': ticket, 'symbol': sym, 'fraction': 0.25}})
                actions.append({'label': 'Partial 50%', 'action': 'partial_close_50', 'params': {'ticket': ticket, 'symbol': sym, 'fraction': 0.50}})
            # ATR-based trailing suggestion from recent M15 bars
            try:
                from .pulse.service import _load_minute_data  # reuse loader
                import pandas as _p
                bars = _load_minute_data(sym).get('M15')
                if bars is not None and not bars.empty and {'high','low','close'}.issubset(set(bars.columns)):
                    tr = (bars['high'] - bars['low']).abs()
                    atr14 = float(_p.to_numeric(tr, errors='coerce').rolling(14, min_periods=5).mean().iloc[-1])
                    if atr14 and atr14 > 0:
                        if typ == 'BUY':
                            lock = pc - 1.0 * atr14
                        else:
                            lock = pc + 1.0 * atr14
                        actions.append({'label': 'Trail SL (ATR14)', 'action': 'protect_trail_atr', 'params': {'ticket': ticket, 'symbol': sym, 'atr14': round(atr14, 5), 'suggested_sl': round(lock, 5)}})
            except Exception:
                pass
            # Structure-based stop (if recent swing available via structure gate)
            try:
                from app.nexus.pulse.gates import structure_gate  # type: ignore
                m1 = _load_minute_data(sym).get('M1')
                st = structure_gate(m1) if m1 is not None else {"passed": False}
                choch_price = st.get('choch_price') if isinstance(st, dict) else None
                if choch_price is not None:
                    sl = float(choch_price)
                    actions.append({'label': 'Structure SL (CHoCH)', 'action': 'protect_structure_sl', 'params': {'ticket': ticket, 'symbol': sym, 'suggested_sl': round(sl, 5)}})
            except Exception:
                pass
            return Response({'actions': actions})
        except Exception:
            return Response({'actions': []})


class UserPrefsView(views.APIView):
    """Very small, unauthenticated user prefs store.

    GET  /api/v1/user/prefs -> { favorite_symbol?: str }
    POST /api/v1/user/prefs { favorite_symbol?: str } -> { ok: true }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        out = {}
        try:
            r = _redis_client()
            if r is not None:
                raw = r.get('user:prefs')
                if raw:
                    import json as _json
                    out = _json.loads(raw)
        except Exception:
            out = {}
        return Response(out)

    def post(self, request):
        data = request.data or {}
        fav = data.get('favorite_symbol')
        try:
            r = _redis_client()
            if r is None:
                return Response({'error': 'redis unavailable'}, status=503)
            import json as _json
            # Merge with existing prefs if present
            current = {}
            raw = r.get('user:prefs')
            if raw:
                try:
                    current = _json.loads(raw)
                except Exception:
                    current = {}
            if fav:
                current['favorite_symbol'] = str(fav).upper()
            r.set('user:prefs', _json.dumps(current))
            return Response({'ok': True, **current})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class HistoryDealsProxyView(views.APIView):
    """Proxy MT5 history_deals_get endpoint."""
    permission_classes = [AllowAny]

    def get(self, request):
        base = (
            os.getenv("MT5_URL")
            or os.getenv("MT5_API_URL")
            or "http://mt5:5000"
        )
        try:
            r = requests.get(
                f"{str(base).rstrip('/')}/history_deals_get",
                params=request.GET,
                timeout=5,
            )
            r.raise_for_status()
            return Response(r.json())
        except Exception as e:
            return Response({"error": str(e)}, status=502)


class HistoryOrdersProxyView(views.APIView):
    """Proxy MT5 history_orders_get endpoint."""
    permission_classes = [AllowAny]

    def get(self, request):
        base = (
            os.getenv("MT5_URL")
            or os.getenv("MT5_API_URL")
            or "http://mt5:5000"
        )
        try:
            r = requests.get(
                f"{str(base).rstrip('/')}/history_orders_get",
                params=request.GET,
                timeout=5,
            )
            r.raise_for_status()
            return Response(r.json())
        except Exception as e:
            return Response({"error": str(e)}, status=502)


class PulseStatusView(views.APIView):
    """Return gate statuses for the PULSE Predictive Flow Framework.

    Response shape: {"context": 0|1, "liquidity": 0|1, "structure": 0|1,
                     "imbalance": 0|1, "risk": 0|1, "confluence": 0|1}
    Values are best-effort from Redis key 'pulse:status' when present, else zeros.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        gates = {k: 0 for k in [
            'context', 'liquidity', 'structure', 'imbalance', 'risk', 'confluence'
        ]}
        try:
            r = _redis_client()
            if r is not None:
                raw = r.get('pulse:status')
                if raw:
                    import json as _json
                    data = _json.loads(raw)
                    for k in list(gates.keys()):
                        v = data.get(k)
                        if isinstance(v, bool):
                            gates[k] = 1 if v else 0
                        elif isinstance(v, (int, float)):
                            gates[k] = 1 if float(v) > 0 else 0
        except Exception:
            pass
        return Response(gates)
