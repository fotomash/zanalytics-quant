from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class PlaybookSessionInit(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        n = 3
        try:
            n = max(1, min(10, int(request.data.get("n_strategies", 3))))
        except Exception:
            n = 3
        strategies: List[Dict[str, Any]] = []
        for i in range(n):
            strategies.append({
                "name": f"Strategy {i+1}",
                "score": round(1.0 - i * (1.0 / max(1, n)), 3),
                "rationale": "stub",
                "params": {},
            })
        return Response({
            "session_id": str(uuid.uuid4()),
            "strategies": strategies,
        })


class LiquidityMapView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        sym = request.query_params.get("symbol") or "XAUUSD"
        levels = [
            {"price": 2365.0, "kind": "swing_high", "strength": 0.9},
            {"price": 2352.5, "kind": "imbalance",  "strength": 0.7},
            {"price": 2344.0, "kind": "swing_low",  "strength": 0.6},
        ]
        return Response({
            "asof": datetime.utcnow().isoformat() + "Z",
            "levels": levels,
        })


class PriorityItemsView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cands = request.data.get("candidates") or []
        items: List[Dict[str, Any]] = []
        for idx, c in enumerate(cands):
            try:
                sym = c.get("symbol")
            except Exception:
                sym = str(c)
            items.append({
                "symbol": sym,
                "priority": idx + 1,
                "reason": "stub",
            })
        return Response({"items": items})


class ExplainSignalView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        sig = (request.data or {}).get("signal") or ""
        return Response({
            "explanation": f"Explanation for '{sig}' (stub).",
            "journal_id": None,
        })


class DailySummaryView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "date": date.today().isoformat(),
            "equity_open": 100000,
            "equity_close": 100350,
            "pnl_day": 350,
            "best_trades": [],
        })

