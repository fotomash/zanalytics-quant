from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .orders_service import (
    place_market_order,
    modify_sl_tp,
    close_position_partial_or_full,
    get_account_info,
    get_position,
)
from .journal_service import journal_append


class PositionsCloseView(APIView):
    """POST /api/v1/positions/close

    Body: { ticket: int, fraction?: float, volume?: float }
    If neither fraction nor volume is provided → full close.
    """

    def post(self, request):
        payload = request.data or {}
        ticket = payload.get("ticket")
        if ticket is None:
            return Response({"error": "ticket required"}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: verify position exists for clearer error messages
        pos = get_position(ticket)
        if not pos:
            return Response({"error": f"position {ticket} not found"}, status=status.HTTP_404_NOT_FOUND)

        fraction = payload.get("fraction")
        volume = payload.get("volume")
        ok, data = close_position_partial_or_full(
            ticket=int(ticket),
            fraction=fraction,
            volume=volume,
            idempotency_key=request.headers.get("X-Idempotency-Key"),
        )
        if ok:
            action = "PARTIAL_CLOSE" if (fraction is not None or volume is not None) else "CLOSE"
            journal_append(kind=action, text=f"Closed ticket={ticket}", meta={"req": payload, "resp": data})
            return Response(data)
        return Response(data, status=status.HTTP_400_BAD_REQUEST)


class PositionsModifyView(APIView):
    """POST /api/v1/positions/modify

    Body: { ticket: int, sl?: float, tp?: float }
    """

    def post(self, request):
        payload = request.data or {}
        ticket = payload.get("ticket")
        if ticket is None:
            return Response({"error": "ticket required"}, status=status.HTTP_400_BAD_REQUEST)
        ok, data = modify_sl_tp(
            ticket=int(ticket),
            sl=payload.get("sl"),
            tp=payload.get("tp"),
            idempotency_key=request.headers.get("X-Idempotency-Key"),
        )
        if ok:
            journal_append(kind="ORDER_MODIFY", text=f"Modify SL/TP ticket={ticket}", meta={"req": payload, "resp": data})
            return Response(data)
        return Response(data, status=status.HTTP_400_BAD_REQUEST)


class PositionsHedgeView(APIView):
    """POST /api/v1/positions/hedge

    Body: { ticket: int, volume?: float }
    Opens an opposite-side market order to hedge the position.
    Note: on netting accounts, this nets exposure rather than opening a separate hedge.
    """

    def post(self, request):
        payload = request.data or {}
        ticket = payload.get("ticket")
        if ticket is None:
            return Response({"error": "ticket required"}, status=status.HTTP_400_BAD_REQUEST)

        pos = get_position(ticket)
        if not pos:
            return Response({"error": f"position {ticket} not found"}, status=status.HTTP_404_NOT_FOUND)

        # Infer hedge side: opposite of the existing position type
        ptype = pos.get("type")  # could be numeric (0/1) or string
        try:
            ptype_num = int(ptype)
            side = "sell" if ptype_num == 0 else "buy"
        except Exception:
            # Fallback if string
            side = "sell" if str(ptype).lower().startswith("buy") else "buy"

        volume = payload.get("volume") or pos.get("volume")
        ok, data = place_market_order(
            symbol=pos.get("symbol"),
            volume=float(volume),
            side=side,
            comment=f"hedge ticket={ticket}",
            idempotency_key=request.headers.get("X-Idempotency-Key"),
        )
        acct = get_account_info() or {}
        if ok:
            note = "Hedge placed."
            if str(acct.get("mode")).lower().startswith("net"):
                note = "Account likely in netting mode; hedge nets exposure."
            data["note"] = note
            journal_append(kind="ORDER_HEDGE", text=f"Hedged ticket={ticket}", meta={"req": payload, "resp": data})
            return Response(data)
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

