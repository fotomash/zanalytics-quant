#!/usr/bin/env python3
"""Backtest slice runner for EchoNudge/Whisperer KPIs.

Reads a CSV of tick or event rows and computes:
- Tail risk reduction: delta in max single-day drawdown vs baseline
- Hit rate on cautions: P(ae_pct > X) | caution in {med,high}
- Missed-opportunity cost: net R lost when blocking winners
- Escalation rate: % rows that escalated to Whisperer
- Decision latency: p50/p95 added ms (EchoNudge and total when escalated)
- Clarity: % rows with clean JSON and reason length <= 18

CSV expectations (best effort, flexible):
- Required for caution eval: symbol, ts (ISO), phase, price, volume,
  rsi, sweep_prob, corr_cluster, confidence, recent_loss_setups.
- Optional for Whisperer prompt: bars_window, confidence_trace, rule_matches,
  session_refs, aversion_mult, hedge_price, rule_id
- Ground-truth metrics (optional but recommended):
  - ae_pct: adverse excursion percentage over the evaluation horizon
  - outcome_r or r: realized R of the setup

Example:
  python scripts/backtest_slice.py --csv data/week_eurusd_m5.csv --ae-thr 0.6 --block-policy med_high
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as stats
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utils.correlation_intelligence_engine import aware_caution_tick


def _parse_float(x: Any, default: float | None = None) -> Optional[float]:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if not s:
            return default
        if s.endswith("%"):
            return float(s[:-1])
        return float(s)
    except Exception:
        return default


def _parse_json(x: Any, default: Any = None) -> Any:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if not s:
            return default
        return json.loads(s)
    except Exception:
        return default


def _date(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.utcfromtimestamp(float(ts))
    return dt.strftime("%Y-%m-%d")


@dataclass
class RowResult:
    clean_json: bool
    reason_words: int
    caution: str
    escalated: bool
    echo_ms: float
    total_ms: float
    ae_pct: Optional[float]
    outcome_r: float
    day: str


def _ctx_from_row(row: dict[str, Any]) -> Dict[str, Any]:
    # Minimal fields; provide defaults if missing
    return {
        "symbol": row.get("symbol", "EURUSD"),
        "ts": row.get("ts") or row.get("timestamp") or datetime.utcnow().isoformat(),
        "phase": row.get("phase", "neutral"),
        "price": _parse_float(row.get("price")) or 0.0,
        "volume": _parse_float(row.get("volume")) or 0.0,
        "rsi": _parse_float(row.get("rsi")) or 50.0,
        "sweep_prob": _parse_float(row.get("sweep_prob")) or 0.0,
        "corr_cluster": _parse_float(row.get("corr_cluster")) or 0.0,
        "confidence": _parse_float(row.get("confidence")) or 0.0,
        "rule_matches": _parse_json(row.get("rule_matches")) or [],
        "recent_loss_setups": int(_parse_float(row.get("recent_loss_setups"), 0) or 0),
        "recent_missed_rr": row.get("recent_missed_rr", "0R"),
        "journal_note": row.get("journal_note", ""),
        # Optional Whisperer extras
        "bars_window": row.get("bars_window") or "[]",
        "confidence_trace": _parse_json(row.get("confidence_trace")) or {"raw": 0.5, "sim": 0.3, "norm": 0.2},
        "session_refs": _parse_json(row.get("session_refs")) or [],
        "aversion_mult": _parse_float(row.get("aversion_mult")) or 2.0,
        "hedge_price": _parse_float(row.get("hedge_price")) or ( _parse_float(row.get("price")) or 0.0 ),
        "rule_id": row.get("rule_id", "corr_gt_0_8"),
    }


def evaluate_rows(rows: Iterable[dict[str, Any]], *, ae_thr: float, block_policy: str) -> Dict[str, Any]:
    results: List[RowResult] = []
    # Accumulate PnL series baseline and with-guard per day
    pnl_base: Dict[str, List[float]] = defaultdict(list)
    pnl_guard: Dict[str, List[float]] = defaultdict(list)

    for row in rows:
        ctx = _ctx_from_row(row)
        start = datetime.now().timestamp()
        out_ctx = aware_caution_tick(ctx.copy())
        mid = datetime.now().timestamp()
        # Summaries
        caution = str(out_ctx.get("caution") or "none")
        reason = str(out_ctx.get("caution_reason") or "")
        clean = bool(caution in {"none", "low", "medium", "high"}) and (len(reason.split()) <= 18 if reason else True)
        escalated = out_ctx.get("ae_pct") is not None or out_ctx.get("rr_if_hedged") is not None

        ae_pct = _parse_float(row.get("ae_pct"))
        r = _parse_float(row.get("outcome_r"))
        if r is None:
            r = _parse_float(row.get("r"), 0.0) or 0.0
        day = _date(str(ctx["ts"]))

        echo_ms = (mid - start) * 1000.0
        total_ms = (datetime.now().timestamp() - start) * 1000.0

        results.append(RowResult(
            clean_json=clean,
            reason_words=len(reason.split()) if reason else 0,
            caution=caution,
            escalated=bool(escalated),
            echo_ms=echo_ms,
            total_ms=total_ms,
            ae_pct=ae_pct,
            outcome_r=r,
            day=day,
        ))

        # PnL streams
        pnl_base[day].append(r)
        blocked = (caution == "high") if block_policy == "high" else (caution in {"medium", "high"})
        pnl_guard[day].append(0.0 if blocked else r)

    # Metrics
    n = len(results)
    if n == 0:
        return {"error": "no rows"}

    escalation_rate = sum(1 for r in results if r.escalated) / n
    echo_lat = sorted(r.echo_ms for r in results)
    total_lat = sorted(r.total_ms for r in results)

    def pct(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        k = max(0, min(len(values) - 1, int(math.ceil(p * len(values))) - 1))
        return float(values[k])

    p50_echo, p95_echo = pct(echo_lat, 0.5), pct(echo_lat, 0.95)
    p50_total, p95_total = pct(total_lat, 0.5), pct(total_lat, 0.95)

    # Clarity
    clarity = sum(1 for r in results if r.clean_json) / n

    # Hit rate on cautions
    caut_rows = [r for r in results if r.caution in {"medium", "high"} and r.ae_pct is not None]
    hit = sum(1 for r in caut_rows if (r.ae_pct or 0) > ae_thr)
    hit_rate = (hit / len(caut_rows)) if caut_rows else 0.0

    # Missed opportunity: sum of positive R blocked, averaged per day
    missed_per_day: Dict[str, float] = defaultdict(float)
    for r in results:
        blocked = (r.caution == "high") if block_policy == "high" else (r.caution in {"medium", "high"})
        if blocked and r.outcome_r > 0:
            missed_per_day[r.day] += r.outcome_r
    avg_missed_r = (sum(missed_per_day.values()) / max(1, len(missed_per_day))) if missed_per_day else 0.0

    # Tail risk: max single-day drawdown difference baseline vs guard
    def max_dd(day_stream: List[float]) -> float:
        peak = 0.0
        equity = 0.0
        max_draw = 0.0
        for x in day_stream:
            equity += x
            peak = max(peak, equity)
            max_draw = min(max_draw, equity - peak)
        return max_draw  # negative value

    dd_base = {d: max_dd(vals) for d, vals in pnl_base.items()}
    dd_guard = {d: max_dd(pnl_guard[d]) for d in pnl_base.keys()}
    # Reduction: average improvement in drawdown (positive is good)
    dd_reduction = stats.mean([(dd_guard[d] - dd_base[d]) for d in dd_base.keys()]) if dd_base else 0.0

    return {
        "count": n,
        "escalation_rate": escalation_rate,
        "latency_ms": {"echo_p50": p50_echo, "echo_p95": p95_echo, "total_p50": p50_total, "total_p95": p95_total},
        "clarity": clarity,
        "hit_rate_cautions": hit_rate,
        "avg_missed_r_per_day": avg_missed_r,
        "dd_reduction": dd_reduction,
    }


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Backtest slice KPIs for EchoNudge/Whisperer")
    p.add_argument("--csv", required=True, help="Input CSV with tick/features and ground truth columns")
    p.add_argument("--ae-thr", type=float, default=0.6, help="Adverse excursion threshold for hits")
    p.add_argument("--block-policy", choices=["high", "med_high"], default="high", help="Block on high or on medium+high cautions")
    args = p.parse_args(argv)

    with open(args.csv, newline="") as fh:
        rows = list(csv.DictReader(fh))
    report = evaluate_rows(rows, ae_thr=args.ae_thr, block_policy=args.block_policy)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()

