import os
import sys
import json
import requests


API_URL = os.getenv("API_URL", "http://localhost:8010").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN")


def _headers():
    h = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    return h


def test_trades_db(limit: int = 5):
    print("[Test] Checking DB-backed trades_recent…")
    resp = requests.post(
        f"{API_URL}/api/v1/actions/query",
        headers=_headers(),
        json={"type": "trades_recent", "payload": {"limit": int(limit)}},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    # In slim spec, trades_recent returns an array of TradeItem
    if isinstance(data, list):
        print(f"[DB Result] items={len(data)} sample={json.dumps(data[:2], indent=2)}")
        return data
    print(f"[DB Result] unexpected: {data}")
    return []


def test_trades_mt5(date_from: str = "2025-09-01", limit: int = 5):
    print("[Test] Checking MT5 live trades…")
    resp = requests.post(
        f"{API_URL}/api/v1/actions/query",
        headers=_headers(),
        json={"type": "trades_history_mt5", "payload": {"date_from": date_from}},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    # trades_history_mt5 returns an array of history items
    if isinstance(data, list):
        out = data[: int(limit)]
        print(f"[MT5 Result] items={len(out)} sample={json.dumps(out[:2], indent=2)}")
        return out
    print(f"[MT5 Result] unexpected: {data}")
    return []


if __name__ == "__main__":
    try:
        db_trades = test_trades_db()
        if not db_trades:
            print("[Test] No DB trades found → falling back to MT5")
            _ = test_trades_mt5()
        else:
            print("[Test] DB returned trades; MT5 fallback not needed")
    except Exception as e:
        print("[Test] Error:", e, file=sys.stderr)
        sys.exit(1)

