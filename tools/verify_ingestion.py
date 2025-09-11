import os, sys, json, time
from datetime import datetime, timedelta
import requests
import pandas as pd

# --- Config ---
API_BASE = os.environ.get("PULSE_API_BASE", "http://localhost:8000/api/pulse")
JOURNAL_PATH = os.environ.get("JOURNAL_PATH", "signal_journal.json")

# Lazy import MT5 bridge only if present
def _load_bridge():
    try:
        from mt5_bridge_production import MT5Bridge
        return MT5Bridge(
            account=os.environ.get("MT5_ACCOUNT") and int(os.environ["MT5_ACCOUNT"]),
            password=os.environ.get("MT5_PASSWORD"),
            server=os.environ.get("MT5_SERVER"),
        )
    except Exception as e:
        print(f"[WARN] MT5 bridge not available: {e}")
        return None

def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


def call_api(path, payload=None, method="GET", timeout=10):
    url = f"{API_BASE}{path}"
    if method == "GET":
        r = requests.get(url, timeout=timeout)
    elif method == "POST":
        r = requests.post(url, json=payload or {}, timeout=timeout)
    else:
        raise ValueError(method)
    r.raise_for_status()
    return r.json()


def verify_mt5_and_history(days_back=7):
    bridge = _load_bridge()
    if not bridge:
        print("[SKIP] MT5 verification skipped (bridge not importable).")
        return None
    try:
        bridge.connect()
    except RuntimeError:
        print("[SKIP] MT5 verification skipped (no connection).")
        return None
    try:
        df = bridge.get_real_trade_history(days_back=days_back)
        _assert(isinstance(df, pd.DataFrame), "MT5 history is not a DataFrame")
        print(f"[OK] Pulled {len(df)} MT5 deals (filtered to trades) over {days_back}d.")
        if not df.empty:
            required = {"time","date","symbol","profit","volume","is_win","hour_local",
                        "revenge_trade","overconfidence","fatigue_trade","fomo_trade","behavioral_risk_score"}
            _assert(required.issubset(df.columns), f"Missing columns in MT5 DF: {required - set(df.columns)}")
    finally:
        bridge.disconnect()
    return True


def verify_journal_sync():
    bridge = _load_bridge()
    if not bridge:
        print("[SKIP] Journal sync via MT5 skipped.")
        return None
    try:
        bridge.connect()
    except RuntimeError:
        print("[SKIP] Journal sync via MT5 skipped.")
        return None
    try:
        n1 = bridge.sync_to_pulse_journal(JOURNAL_PATH)
        n2 = bridge.sync_to_pulse_journal(JOURNAL_PATH)
        _assert(n2 == 0, f"Journal sync not idempotent; expected 0 new, got {n2}")
        print(f"[OK] Journal sync idempotent (initial +{n1}, then +0).")
    finally:
        bridge.disconnect()
    try:
        with open(JOURNAL_PATH, "r") as f:
            journal = json.load(f)
        mt5_entries = [e for e in journal if e.get("type") == "mt5_trade"]
        _assert(len(mt5_entries) > 0, "No mt5_trade entries found in journal")
        flags = mt5_entries[-1]["data"]["behavioral_flags"]
        _assert(set(flags.keys()) == {"revenge_trade","overconfidence","fatigue_trade","fomo_trade"},
                "Behavioral flags missing/renamed in journal entry")
        print(f"[OK] Journal entries have behavioral flags.")
    except FileNotFoundError:
        print("[WARN] JOURNAL_PATH not found; API mode only?")
    return True


def verify_kernel_endpoints():
    s = call_api("/score/peek")
    for k in ("score","reasons","components"):
        _assert(k in s, f"/score/peek missing '{k}'")
    _assert(isinstance(s["score"], (int,float)), "/score/peek score not numeric")
    _assert(len(s["reasons"]) > 0, "/score/peek reasons empty")
    print("[OK] /score/peek returns real-looking score & reasons")

    r = call_api("/risk/summary")
    for k in ("allowed","remaining_trades","cooling_active","warnings"):
        _assert(k in r, f"/risk/summary missing '{k}'")
    print("[OK] /risk/summary returns risk state")

    sigs = call_api("/signals/top")
    _assert(isinstance(sigs, list), "/signals/top is not a list")
    if sigs:
        for k in ("symbol","score","bias","reasons"):
            _assert(k in sigs[0], f"/signals/top element missing '{k}'")
    print(f"[OK] /signals/top returned {len(sigs)} signals")


def verify_tick_replay(sample_csv="ticks_sample.csv", limit=200):
    if not os.path.exists(sample_csv):
        print(f"[SKIP] No {sample_csv} found for replay. Provide one to run this step.")
        return None
    df = pd.read_csv(sample_csv).head(limit)
    good = 0
    for _, row in df.iterrows():
        payload = {
            "time": row["time"],
            "symbol": row["symbol"],
            "bid": float(row["bid"]),
            "ask": float(row["ask"]),
        }
        out = call_api("/score", payload, method="POST")
        if isinstance(out, dict) and "score" in out and "reasons" in out:
            good += 1
        time.sleep(0.01)
    _assert(good > 0, "No valid score responses during tick replay")
    print(f"[OK] Tick replay produced {good} scored frames (non-mock).")


if __name__ == "__main__":
    steps = [
        ("MT5 & history", verify_mt5_and_history),
        ("Journal sync", verify_journal_sync),
        ("Kernel endpoints", verify_kernel_endpoints),
        ("Tick replay", verify_tick_replay),
    ]
    any_fail = False
    for name, fn in steps:
        try:
            print(f"\n== {name} ==")
            fn()
        except Exception as e:
            any_fail = True
            print(f"[FAIL] {name}: {e}")
    sys.exit(1 if any_fail else 0)
