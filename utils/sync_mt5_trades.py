"""MT5 → DB sync scaffolding.

Current behavior:
- Fetches live MT5 closed trades via Actions Bus (read-only) and stores them to CSV for later ingestion.
- Replace `persist_trades` with a Django management command call when ready to write into the Trade model.
"""

import csv
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

import requests


API_URL = os.getenv("API_URL", "http://localhost:8010").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN")
OUT_DIR = os.getenv("MT5_SYNC_OUT", "data/ingest")


def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    return h


def fetch_mt5_trades(date_from: str) -> List[Dict[str, Any]]:
    """Fetch closed trades from MT5 via Actions Bus."""
    resp = requests.post(
        f"{API_URL}/api/v1/actions/query",
        headers=_headers(),
        json={"type": "trades_history_mt5", "payload": {"date_from": date_from}},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def persist_trades(trades: List[Dict[str, Any]]) -> str:
    """Persist trades to CSV for later ingestion.

    Returns path to the created file.
    """
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(OUT_DIR, f"mt5_trades_{ts}.csv")
    fields = ["id", "ts", "symbol", "direction", "entry", "exit", "pnl", "status"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for t in trades:
            row = {k: t.get(k) for k in fields}
            w.writerow(row)
    return path


if __name__ == "__main__":
    start = os.getenv("MT5_SYNC_FROM", datetime.now().strftime("%Y-%m-01"))
    items = fetch_mt5_trades(start)
    out = persist_trades(items)
    print(f"[Sync] Wrote {len(items)} trades to {out}")

