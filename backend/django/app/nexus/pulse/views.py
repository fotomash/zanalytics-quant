from __future__ import annotations

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .service import pulse_status
from .service import _load_minute_data
from .gates import structure_gate, liquidity_gate, imbalance_gate, risk_gate
from app.nexus.views import _redis_client


class PulseStatus(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get("symbol") or "XAUUSD"
        # Optional weight overrides via query params w_context, w_liquidity, ...
        weights = {}
        for k in ("context", "liquidity", "structure", "imbalance", "risk"):
            v = request.query_params.get(f"w_{k}")
            try:
                if v is not None:
                    weights[k] = float(v)
            except Exception:
                pass
        thr = request.query_params.get("threshold") or request.query_params.get("thr")
        try:
            thr_val = float(thr) if thr is not None else None
        except Exception:
            thr_val = None
        try:
            status = pulse_status(symbol, weights=weights or None, threshold=thr_val)
        except Exception:
            # Hard fallback: empty lights rather than erroring
            status = {k: 0 for k in [
                'context', 'liquidity', 'structure', 'imbalance', 'risk', 'confluence'
            ]}
        return Response(status)


class PulseDetail(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get("symbol") or "XAUUSD"
        # Short-circuit cache for 3 seconds to reduce compute
        try:
            r = _redis_client()
            if r is not None:
                key = f"pulse:detail:{symbol}"
                raw = r.get(key)
                if raw:
                    import json as _json
                    return Response(_json.loads(raw))
        except Exception:
            pass
        data = _load_minute_data(symbol)
        try:
            m1 = data.get('M1')
            m15 = data.get('M15')
            struct = structure_gate(m1) if m1 is not None else {"passed": False}
            liq = liquidity_gate(m15) if m15 is not None else {"passed": False}
            imb = imbalance_gate(m1) if m1 is not None else {"passed": False, "entry_zone": [None, None]}
            rsk = risk_gate(imb, struct, symbol)
            # Include confluence summary (same weights/threshold as status endpoint defaults)
            try:
                from .service import _resolve_weights
                from .confluence_score_engine import compute_confluence_score
                w = _resolve_weights(None, symbol=symbol)
                score, reasons = compute_confluence_score(
                    {"context": {"passed": False}, "liquidity": liq, "structure": struct, "imbalance": imb, "risk": rsk},
                    w,
                )
                conf = {"confidence": score, "passed": bool(reasons.get("score_passed"))}
            except Exception:
                conf = {"confidence": 0.0, "passed": False}
            payload = {"structure": struct, "liquidity": liq, "risk": rsk, "confluence": conf}
            try:
                r = _redis_client()
                if r is not None:
                    import json as _json
                    r.setex(f"pulse:detail:{symbol}", 3, _json.dumps(payload))
            except Exception:
                pass
            return Response(payload)
        except Exception:
            return Response({"structure": {"passed": False}, "liquidity": {"passed": False}})


class PulseWeights(views.APIView):
    """Persist and retrieve confluence weights + threshold via Redis.

    GET  -> {"weights": {..}, "threshold": float}
    POST -> accepts JSON with same structure; stores with TTL (optional)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            r = _redis_client()
            symbol = request.query_params.get("symbol") or None
            # Prefer symbol-specific; fallback to global
            key = f"pulse:conf_weights:{symbol}" if symbol else "pulse:conf_weights"
            if r is not None:
                raw = r.get(key)
                if (not raw) and symbol:
                    raw = r.get("pulse:conf_weights")
                if raw:
                    import json as _json
                    return Response(_json.loads(raw))
        except Exception:
            pass
        # Default response if nothing stored
        return Response({
            "weights": {"context": 0.2, "liquidity": 0.2, "structure": 0.25, "imbalance": 0.15, "risk": 0.2},
            "threshold": 0.6,
        })

    def post(self, request):
        try:
            data = request.data or {}
            symbol = data.get("symbol") or None
            weights = data.get("weights") or {}
            threshold = float(data.get("threshold")) if data.get("threshold") is not None else 0.6
            if not isinstance(weights, dict):
                return Response({"error": "weights must be an object"}, status=400)
            # Sanitize
            clean = {k: float(v) for k, v in weights.items() if k in {"context", "liquidity", "structure", "imbalance", "risk"} and isinstance(v, (int, float))}
            payload = {"weights": clean, "threshold": float(threshold)}
            r = _redis_client()
            if r is not None:
                import json as _json
                if symbol:
                    r.set(f"pulse:conf_weights:{symbol}", _json.dumps(payload))
                else:
                    r.set("pulse:conf_weights", _json.dumps(payload))
            return Response({"ok": True, **payload})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class PulseGateHits(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get("symbol")
        try:
            limit = int(request.query_params.get("limit") or 100)
        except Exception:
            limit = 100
        try:
            r = _redis_client()
            items = []
            if r is not None:
                raw_list = r.lrange("pulse:gate_hits", -limit, -1) or []
                import json as _json
                for raw in reversed(raw_list):
                    try:
                        obj = _json.loads(raw)
                        if symbol and obj.get("symbol") != symbol:
                            continue
                        items.append(obj)
                    except Exception:
                        continue
            return Response({"items": items})
        except Exception as e:
            return Response({"items": [], "error": str(e)}, status=500)


class BarsEnriched(views.APIView):
    """Return normalized bars with lightweight enrichments for LLM agents.

    Query:
      symbol: e.g. XAUUSD
      timeframe: one of H4,H1,M15,M1 (default M15)
      limit: max bars to return (<= 800)
      enrich: optional bool (default true) to include basic extras
    """
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get("symbol") or "XAUUSD"
        tf = (request.query_params.get("timeframe") or "M15").upper()
        try:
            limit = int(request.query_params.get("limit") or 300)
        except Exception:
            limit = 300
        try:
            enrich = str(request.query_params.get("enrich") or "true").lower() != "false"
        except Exception:
            enrich = True

        data = _load_minute_data(symbol)
        df = data.get(tf)
        if df is None or df.empty:
            return Response({"items": []})
        # Tail to limit
        df = df.tail(max(1, min(limit, 800))).copy()
        # Basic enrichments
        if enrich:
            try:
                import pandas as _p
                # pct change
                df["ret_close_pct"] = _p.to_numeric(df["close"], errors='coerce').pct_change().fillna(0.0)
                # ATR14 approximation (HL range SMA)
                rng = (_p.to_numeric(df['high'], errors='coerce') - _p.to_numeric(df['low'], errors='coerce')).abs()
                df["atr14"] = rng.rolling(14, min_periods=3).mean()
                # SMA20/50
                df["sma20"] = _p.to_numeric(df['close'], errors='coerce').rolling(20, min_periods=3).mean()
                df["sma50"] = _p.to_numeric(df['close'], errors='coerce').rolling(50, min_periods=3).mean()
                # VWAP (anchored from start)
                tp = (_p.to_numeric(df['high'], errors='coerce') + _p.to_numeric(df['low'], errors='coerce') + _p.to_numeric(df['close'], errors='coerce')) / 3.0
                vol = _p.to_numeric(df['volume'], errors='coerce').fillna(0)
                cumv = vol.cumsum().replace(0, _p.NA)
                df["vwap"] = (tp * vol).cumsum() / cumv
                # Simple Fair Value Gap flags (three-candle model)
                df["fvg_bull"] = False
                df["fvg_bear"] = False
                for i in range(2, len(df)):
                    try:
                        low_i = float(df.iloc[i]["low"]) if _p.notna(df.iloc[i]["low"]) else None
                        high_im2 = float(df.iloc[i-2]["high"]) if _p.notna(df.iloc[i-2]["high"]) else None
                        high_i = float(df.iloc[i]["high"]) if _p.notna(df.iloc[i]["high"]) else None
                        low_im2 = float(df.iloc[i-2]["low"]) if _p.notna(df.iloc[i-2]["low"]) else None
                        if low_i is not None and high_im2 is not None and low_i > high_im2:
                            df.at[df.index[i], "fvg_bull"] = True
                        if high_i is not None and low_im2 is not None and high_i < low_im2:
                            df.at[df.index[i], "fvg_bear"] = True
                    except Exception:
                        continue
            except Exception:
                pass
        # Serialize
        try:
            items = []
            for _, row in df.iterrows():
                try:
                    ts = row.get('timestamp')
                    ts_str = str(ts) if not hasattr(ts, 'isoformat') else ts.isoformat()
                except Exception:
                    ts_str = str(row.get('timestamp'))
                items.append({
                    "timestamp": ts_str,
                    "open": float(row.get('open') or 0),
                    "high": float(row.get('high') or 0),
                    "low": float(row.get('low') or 0),
                    "close": float(row.get('close') or 0),
                    "volume": float(row.get('volume') or 0),
                    "ret_close_pct": float(row.get('ret_close_pct')) if 'ret_close_pct' in df.columns else None,
                    "atr14": float(row.get('atr14')) if 'atr14' in df.columns else None,
                    "sma20": float(row.get('sma20')) if 'sma20' in df.columns else None,
                    "sma50": float(row.get('sma50')) if 'sma50' in df.columns else None,
                    "vwap": float(row.get('vwap')) if 'vwap' in df.columns else None,
                    "fvg_bull": bool(row.get('fvg_bull')) if 'fvg_bull' in df.columns else False,
                    "fvg_bear": bool(row.get('fvg_bear')) if 'fvg_bear' in df.columns else False,
                })
            return Response({"items": items, "symbol": symbol, "timeframe": tf})
        except Exception as e:
            return Response({"items": [], "error": str(e)}, status=500)


class YFBars(views.APIView):
    """Fetch bars via yfinance as a redundant feed for LLM agents.

    Query:
      symbol: e.g. SPY, EURUSD=X, GC=F
      interval: e.g. 1m, 5m, 15m, 1h, 1d (default 1h)
      range: e.g. 5d, 30d, 60d, 1y (default 60d)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        import datetime as _dt
        symbol = request.query_params.get('symbol') or 'SPY'
        interval = request.query_params.get('interval') or '1h'
        rng = request.query_params.get('range') or '60d'
        try:
            import yfinance as _yf
        except Exception as e:
            return Response({"items": [], "error": f"yfinance not available: {e}"}, status=500)
        try:
            tk = _yf.Ticker(symbol)
            hist = tk.history(period=rng, interval=interval)
            if hist is None or hist.empty:
                return Response({"items": []})
            hist = hist.tail(1500)
            items = []
            for idx, row in hist.iterrows():
                ts = idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx
                items.append({
                    "timestamp": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                    "open": float(row.get('Open') or row.get('open') or 0),
                    "high": float(row.get('High') or row.get('high') or 0),
                    "low": float(row.get('Low') or row.get('low') or 0),
                    "close": float(row.get('Close') or row.get('close') or 0),
                    "volume": float(row.get('Volume') or row.get('volume') or 0),
                })
            return Response({"items": items, "symbol": symbol, "interval": interval, "range": rng})
        except Exception as e:
            return Response({"items": [], "error": str(e)}, status=500)
