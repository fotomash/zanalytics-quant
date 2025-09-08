from __future__ import annotations

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .service import pulse_status
from .service import _load_minute_data
from .gates import structure_gate, liquidity_gate, imbalance_gate, risk_gate, wyckoff_gate
from app.nexus.views import _redis_client
from app.nexus.models import Trade
import datetime as _dt
from collections import Counter
from .serializers import PulseDetailSerializer


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
            wyk = wyckoff_gate(m15 if m15 is not None else m1)
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
            payload = {"structure": struct, "liquidity": liq, "wyckoff": wyk, "risk": rsk, "confluence": conf}
            # Validate against serializer (non-fatal)
            try:
                PulseDetailSerializer(data=payload).is_valid(raise_exception=True)
            except Exception:
                pass
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


class TradeQualityDist(views.APIView):
    """Return a lightweight trade quality distribution.

    Tries Redis caches first; falls back to 0 counts if unavailable.
    Heuristics:
      - Looks for recent trade lists under keys:
          trade:history:recent, mt5:history:recent, pulse:trades:recent
      - For each trade, uses any of: 'quality', 'grade', 'setup_grade', 'setup'
        Mapping:
          values starting with 'A' -> A+
          values starting with 'B' -> B
          values starting with 'C' or lower -> C
      - If numeric 'score' exists (0..100), buckets: >=80→A+, 60..79→B, else C.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        counts = Counter({"A+": 0, "B": 0, "C": 0})
        items = []
        try:
            r = _redis_client()
            if r is not None:
                for key in ("trade:history:recent", "mt5:history:recent", "pulse:trades:recent"):
                    raw = r.get(key)
                    if not raw:
                        continue
                    import json as _json
                    try:
                        arr = _json.loads(raw)
                        if isinstance(arr, list):
                            items = arr
                            break
                    except Exception:
                        continue
        except Exception:
            items = []

        def _bucket(obj: dict) -> str:
            # text-based
            for k in ("quality", "grade", "setup_grade", "setup"):
                v = obj.get(k)
                if isinstance(v, str) and v:
                    s = v.strip().upper()
                    if s.startswith("A"):
                        return "A+"
                    if s.startswith("B"):
                        return "B"
                    return "C"
            # numeric score
            for k in ("score", "quality_score"):
                v = obj.get(k)
                try:
                    x = float(v)
                    if 0 <= x <= 1:
                        x *= 100.0
                    if x >= 80:
                        return "A+"
                    if x >= 60:
                        return "B"
                    return "C"
                except Exception:
                    continue
            return "C"

        try:
            for t in items[:200]:
                if isinstance(t, dict):
                    counts[_bucket(t)] += 1
        except Exception:
            pass
        return Response({"labels": ["A+", "B", "C"], "counts": [counts["A+"], counts["B"], counts["C"]]})


# -------------------- Analytics: Trades (Phase 1) -----------------------------

def _parse_date(s: str | None) -> _dt.datetime | None:
    if not s:
        return None
    try:
        return _dt.datetime.fromisoformat(s)
    except Exception:
        try:
            return _dt.datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None


def _filter_trades(qs, request):
    symbol = request.query_params.get("symbol")
    date_from = _parse_date(request.query_params.get("date_from"))
    date_to = _parse_date(request.query_params.get("date_to"))
    strategy = request.query_params.get("strategy")
    status = request.query_params.get("status")  # not used without a field

    if symbol:
        qs = qs.filter(symbol=symbol)
    if strategy:
        qs = qs.filter(strategy=strategy)
    # Use close_time when present, fallback to entry_time
    if date_from:
        qs = qs.filter(entry_time__gte=date_from)
    if date_to:
        qs = qs.filter(entry_time__lte=date_to)
    return qs


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)


def _realized_r(tr: Trade) -> float:
    pnl = _safe_float(tr.pnl)
    dd = abs(_safe_float(tr.max_drawdown))
    if dd <= 0:
        return 0.0 if pnl == 0 else (1.5 if pnl > 0 else -1.0)
    return pnl / dd


def _eff_pair(tr: Trade) -> tuple[float, float]:
    pnl_pos = max(0.0, _safe_float(tr.pnl))
    pot = _safe_float(tr.max_profit)
    if pot <= 0:
        pot = pnl_pos
    return pnl_pos, max(0.0, pot)


def _grade_from_trade(tr: Trade) -> str:
    r = _realized_r(tr)
    if r >= 1.5:
        return "A+"
    if r >= 0.5:
        return "B"
    return "C"


class TradesQuality(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = _filter_trades(Trade.objects.all(), request)
        labels = ["A+", "B", "C"]
        counts = {k: 0 for k in labels}
        for tr in qs[:1000]:
            counts[_grade_from_trade(tr)] += 1
        return Response({"labels": labels, "counts": [counts[l] for l in labels]})


class TradesSummary(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = _filter_trades(Trade.objects.all(), request)
        n = qs.count()
        if n == 0:
            return Response({
                "win_rate": 0.0,
                "expectancy_r": 0.0,
                "avg_r": 0.0,
                "std_r": 0.0,
                "median_duration_s": 0,
                "trades": 0,
                "pnl_usd": {"total": 0.0, "avg": 0.0},
            })
        rs = []
        pnls = []
        wins = 0
        durs = []
        for tr in qs[:2000]:
            r = _realized_r(tr)
            rs.append(r)
            p = _safe_float(tr.pnl)
            pnls.append(p)
            if p > 0:
                wins += 1
            try:
                if tr.entry_time and tr.close_time:
                    durs.append((tr.close_time - tr.entry_time).total_seconds())
            except Exception:
                pass
        import statistics as _st
        win_rate = wins / max(1, len(pnls))
        avg_r = _st.mean(rs) if rs else 0.0
        std_r = (_st.pstdev(rs) if len(rs) > 1 else 0.0) if rs else 0.0
        expectancy_r = avg_r
        total_pnl = sum(pnls)
        avg_pnl = _st.mean(pnls) if pnls else 0.0
        med_dur = int(_st.median(durs)) if durs else 0
        return Response({
            "win_rate": round(win_rate, 4),
            "expectancy_r": round(expectancy_r, 4),
            "avg_r": round(avg_r, 4),
            "std_r": round(std_r, 4),
            "median_duration_s": med_dur,
            "trades": len(pnls),
            "pnl_usd": {"total": round(total_pnl, 2), "avg": round(avg_pnl, 2)},
        })


class TradesEfficiency(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = _filter_trades(Trade.objects.all(), request)
        cap = 0.0
        pot = 0.0
        effs = []
        for tr in qs[:2000]:
            got, mx = _eff_pair(tr)
            cap += got
            pot += mx
            if mx > 0:
                effs.append(min(1.0, got / mx))
        pct = (cap / pot) if pot > 0 else 0.0
        avg_eff = (sum(effs) / len(effs)) if effs else pct
        return Response({
            "captured_vs_potential_pct": round(pct, 4),
            "avg_efficiency_pct": round(avg_eff, 4),
        })


class TradesBuckets(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = _filter_trades(Trade.objects.all(), request)
        edges = [-3, -2, -1, 0, 1, 2, 3]
        counts = [0 for _ in range(len(edges))]
        for tr in qs[:5000]:
            r = _realized_r(tr)
            # clamp to edges range and bin to nearest edge index
            # bins: (-inf,-2.5],(-2.5,-1.5],...,(2.5,inf)
            idx = min(len(edges) - 1, max(0, int(round(r + 3))))
            counts[idx] += 1
        return Response({"edges": edges, "counts": counts})


class TradesSetups(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = _filter_trades(Trade.objects.all(), request)
        from collections import defaultdict
        agg = defaultdict(lambda: {"A+": 0, "B": 0, "C": 0})
        for tr in qs[:5000]:
            name = tr.strategy or "unknown"
            g = _grade_from_trade(tr)
            agg[name][g] += 1
        setups = []
        for name, d in agg.items():
            item = {"name": name, "A+": d["A+"], "B": d["B"], "C": d["C"]}
            setups.append(item)
        # sort by total desc
        setups.sort(key=lambda x: x["A+"] + x["B"] + x["C"], reverse=True)
        return Response({"setups": setups})


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
        from .yf_config import get_yf_defaults
        enabled, def_interval, def_range, max_points, proxy, cfg = get_yf_defaults()
        if not enabled:
            return Response({"items": [], "error": "yfinance backup disabled"}, status=503)
        symbol = request.query_params.get('symbol') or 'SPY'
        interval = request.query_params.get('interval') or def_interval
        rng = request.query_params.get('range') or def_range
        try:
            import yfinance as _yf
        except Exception as e:
            return Response({"items": [], "error": f"yfinance not available: {e}"}, status=500)
        try:
            tk = _yf.Ticker(symbol)
            # yfinance supports a proxy kw for requests; not all versions honor it
            kwargs = {}
            if proxy:
                kwargs["proxy"] = proxy
            hist = tk.history(period=rng, interval=interval, **kwargs)
            if hist is None or hist.empty:
                return Response({"items": []})
            hist = hist.tail(max_points)
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
