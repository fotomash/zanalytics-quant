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


def _alias(d: dict, key: str, *aliases: str, default=None):
    """Return value for key or first found alias; ignore unknown keys."""
    if key in d and d[key] is not None:
        return d[key]
    for a in aliases:
        if a in d and d[a] is not None:
            return d[a]
    return default


class PositionsOpenView(APIView):
    """POST /api/v1/positions/open

    Body: { symbol: str, side: str, volume: float, sl?: float, tp?: float }
    Accepts aliases: instrument→symbol, action→side, lots/qty→volume.
    """

    def post(self, request):
        data = request.data or {}
        symbol = _alias(data, "symbol", "instrument")
        side = (_alias(data, "side", "action") or "").lower()
        volume_raw = _alias(data, "volume", "lots", "qty")
        try:
            volume = float(volume_raw)
        except (TypeError, ValueError):
            volume = None
        sl = data.get("sl")
        tp = data.get("tp")
        if not symbol or side not in ("buy", "sell") or volume is None or volume <= 0:
            return Response({"error": "symbol, volume, side required"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        ok, resp = place_market_order(
            symbol=symbol,
            side=side,
            volume=volume,
            sl=sl,
            tp=tp,
            idempotency_key=request.headers.get("X-Idempotency-Key"),
        )
        if ok:
            return Response(resp)
        return Response(resp, status=status.HTTP_502_BAD_GATEWAY)


class PositionsCloseView(APIView):
    """POST /api/v1/positions/close

    Body: { ticket: int, fraction?: float, volume?: float }
    If neither fraction nor volume is provided → full close.
    """

    def post(self, request):
        payload = request.data or {}
        ticket = _alias(payload, "ticket", "id")
        if ticket is None:
            return Response({"error": "ticket required"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

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
            # Build structured meta
            try:
                vol_before = float(pos.get("volume")) if pos.get("volume") is not None else None
                if volume is not None:
                    vol_action = float(volume)
                elif fraction is not None and vol_before is not None:
                    vol_action = max(0.0, vol_before * float(fraction))
                else:
                    vol_action = vol_before
                vol_remaining = None
                if vol_before is not None and vol_action is not None:
                    vol_remaining = max(0.0, float(vol_before) - float(vol_action))
                ptype = pos.get("type")
                try:
                    pnum = int(ptype)
                    side = "BUY" if pnum == 0 else "SELL"
                except Exception:
                    side = "BUY" if str(ptype).lower().startswith("buy") else "SELL"
                meta = {
                    "ticket": int(ticket),
                    "symbol": pos.get("symbol"),
                    "side": side,
                    "volume_before": vol_before,
                    "volume_action": vol_action,
                    "volume_remaining": vol_remaining,
                    "reason": "manual_request",
                }
            except Exception:
                meta = {"req": payload, "resp": data}
            journal_append(
                kind=action,
                text=(f"Closed {float(fraction)*100:.0f}% of {pos.get('symbol')}" if fraction is not None else f"Closed ticket={ticket}"),
                meta=meta,
                trade_id=int(ticket),
                tags=["position_close", "partial" if action == "PARTIAL_CLOSE" else "full"],
            )
            return Response(data)
        return Response(data, status=status.HTTP_502_BAD_GATEWAY)


class PositionsModifyView(APIView):
    """POST /api/v1/positions/modify

    Body: { ticket: int, sl?: float, tp?: float }
    """

    def post(self, request):
        payload = request.data or {}
        ticket = _alias(payload, "ticket", "id")
        if ticket is None:
            return Response({"error": "ticket required"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        sl = payload.get("sl")
        tp = payload.get("tp")
        if sl is None and tp is None:
            return Response({"error": "Provide sl and/or tp"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        ok, data = modify_sl_tp(
            ticket=int(ticket),
            sl=sl,
            tp=tp,
            idempotency_key=request.headers.get("X-Idempotency-Key"),
        )
        if ok:
            meta = {
                "ticket": int(ticket),
                "sl": payload.get("sl"),
                "tp": payload.get("tp"),
                "reason": "manual_request",
            }
            journal_append(kind="ORDER_MODIFY", text=f"Modify SL/TP ticket={ticket}", meta=meta, trade_id=int(ticket), tags=["order_modify"])
            return Response(data)
        return Response(data, status=status.HTTP_502_BAD_GATEWAY)


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
            meta = {
                "ticket": int(ticket),
                "symbol": pos.get("symbol"),
                "side": "SELL" if side == "sell" else "BUY",
                "volume_action": float(volume) if volume is not None else float(pos.get("volume")),
                "reason": "manual_request",
            }
            journal_append(kind="HEDGE", text=f"Hedged ticket={ticket}", meta=meta, trade_id=int(ticket), tags=["hedge"])            
            return Response(data)
        return Response(data, status=status.HTTP_400_BAD_REQUEST)
