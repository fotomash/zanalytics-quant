#!/usr/bin/env python3
"""
Lightweight Yahoo Finance chart client + flattener.

- Fetches chart JSON directly from query1.finance.yahoo.com
- Reconstructs OHLCV bars from timestamp + quote arrays
"""
from __future__ import annotations

import sys
import json
import argparse
from typing import List, Dict, Any
import datetime as dt
import requests


def fetch_chart(symbol: str, interval: str = "1h", rng: str = "60d") -> Dict[str, Any]:
    base = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol
    r = requests.get(base, params={"interval": interval, "range": rng}, timeout=6)
    r.raise_for_status()
    return r.json()


def flatten_bars(chart_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = chart_json.get("chart", {}).get("result", [])
    if not result:
        return []
    r0 = result[0]
    ts = r0.get("timestamp") or []
    q = (r0.get("indicators", {}).get("quote") or [{}])[0]
    o = q.get("open") or []
    h = q.get("high") or []
    l = q.get("low") or []
    c = q.get("close") or []
    v = q.get("volume") or []
    n = min(len(ts), len(o), len(h), len(l), len(c), len(v))
    bars: List[Dict[str, Any]] = []
    for i in range(n):
        if None in (o[i], h[i], l[i], c[i]):
            continue
        t = dt.datetime.utcfromtimestamp(int(ts[i]))
        bars.append({
            "timestamp": t.isoformat() + "Z",
            "open": float(o[i]),
            "high": float(h[i]),
            "low": float(l[i]),
            "close": float(c[i]),
            "volume": float(v[i] or 0),
        })
    return bars


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Fetch + flatten Yahoo Finance bars")
    ap.add_argument("symbol", help="Ticker, e.g. SPY or EURUSD=X")
    ap.add_argument("--interval", default="1h", help="e.g. 1m, 15m, 1h, 1d")
    ap.add_argument("--range", dest="rng", default="60d", help="e.g. 5d, 30d, 60d, 1y")
    args = ap.parse_args(argv)
    data = fetch_chart(args.symbol, args.interval, args.rng)
    bars = flatten_bars(data)
    print(json.dumps({"symbol": args.symbol, "interval": args.interval, "range": args.rng, "items": bars}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

