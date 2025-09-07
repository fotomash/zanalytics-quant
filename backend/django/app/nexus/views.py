from rest_framework import viewsets, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from django.views import View
from django.db import connection
import time
from .models import Trade, TradeClosePricesMutation, Tick, Bar, PsychologicalState, JournalEntry
from .serializers import (
    TradeSerializer,
    TradeClosePricesMutationSerializer,
    TickSerializer,
    BarSerializer,
    PsychologicalStateSerializer,
    JournalEntrySerializer,
)
from .filters import TradeFilter, TickFilter, BarFilter

from app.utils.api.order import send_market_order, modify_sl_tp
from app.utils.arithmetics import convert_lots_to_usd, calculate_commission, get_price_at_pnl
from app.utils.policies import load_policies
import os
import requests
import json

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
        data = request.data
        required_fields = ['id', 'ticket', 'stop_loss', 'take_profit']
        for field in required_fields:
            if field not in data:
                return Response({'error': f'Missing field: {field}'}, status=status.HTTP_400_BAD_REQUEST)
        
        id = data.get('id')
        ticket = data.get('ticket')
        stop_loss = data.get('stop_loss')
        take_profit = data.get('take_profit')

        modify_response = modify_sl_tp(
            id=id,
            ticket=ticket,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        if not modify_response:
            return Response({'error': 'Failed to modify SL/TP.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            mutation = TradeClosePricesMutation.objects.filter(trade__id=id).latest('mutation_time')
            mutation_serializer = TradeClosePricesMutationSerializer(mutation)

            return Response({'mutation': mutation_serializer.data}, status=status.HTTP_201_CREATED)
        except TradeClosePricesMutation.DoesNotExist:
            return Response({'error': 'Mutation created but not found in database.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        return Response(payload)


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
        return Response(payload)


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

            result = modify_sl_tp(pobj, sl=new_sl, tp=None)
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

        payload = {
            "balance_usd": balance,
            "pnl_total_pct": None,
            "pnl_inception_momentum_pct": None,
            "pnl_ytd_pct": None,
            "markers": {
                "inception": None,
                "prev_close": equity_prev or None,
                "ath_balance": None,
                "atl_balance": None,
            },
            "awaiting": {
                "pnl_ytd_pct": True,
                "pnl_inception_momentum_pct": True,
            },
        }
        _publish_feed("balance", payload)
        return Response(payload)


class FeedEquityView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        sod = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        closed_today = Trade.objects.filter(close_time__gte=sod, close_time__isnull=False)
        pnl_today = sum([t.pnl or 0 for t in closed_today])
        payload = {
            "session_pnl": pnl_today,
            "pct_to_target": None,
            "risk_used_pct": None,
            "exposure_pct": None,
            "markers": {
                "daily_target": None,
                "daily_loss_limit": None,
                "account_drawdown_hard": None,
            },
        }
        _publish_feed("equity", payload)
        return Response(payload)


class FeedTradeView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        payload = {
            "pnl_day_vs_goal": None,
            "realized_usd": None,
            "unrealized_usd": None,
            "profit_efficiency": None,
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
            out.append({
                "id": str(t.id),
                "dur_min": dur,
                "pnl_r": None,
                "peak_r": None,
            })
        _publish_feed("profit-horizon", {"items": out})
        return Response(out)
