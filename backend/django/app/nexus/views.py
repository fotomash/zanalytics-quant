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
from app.utils.policies import load_policies
import os
import requests


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
        confluence = None
        risk_summary = None
        opportunities = []
        recent_journal_payload = []
        try:
            # risk summary
            rs = requests.get(f"{dj_url}/api/pulse/risk/summary", timeout=2)
            if rs.ok:
                risk_summary = rs.json()
        except Exception:
            risk_summary = None
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

        payload = {
            "psychological_state": psych_payload,
            "confluence_score": confluence,
            "risk_metrics": risk_metrics,
            "risk_summary": risk_summary,
            "opportunities": opportunities,
            "recent_journal": recent_journal_payload,
            "policies": load_policies(),
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
