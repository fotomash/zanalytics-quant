import os
import time
from apscheduler.schedulers.background import BackgroundScheduler
from utils.sync_mt5_trades import fetch_mt5_trades, persist_trades


SYNC_MODE = os.getenv("SYNC_MODE", "hourly").lower()  # "hourly" or "nightly"
DATE_FROM = os.getenv("MT5_SYNC_FROM", "2025-09-01")


def run_sync():
    print("[SyncScheduler] Running MT5 → CSV trade export…")
    trades = fetch_mt5_trades(DATE_FROM)
    path = persist_trades(trades)
    print(f"[SyncScheduler] Exported {len(trades)} trades to {path}")


def start_scheduler():
    scheduler = BackgroundScheduler()

    if SYNC_MODE == "hourly":
        scheduler.add_job(run_sync, "cron", minute=0)  # every hour
        print("[SyncScheduler] Scheduled hourly sync (on the hour).")
    elif SYNC_MODE == "nightly":
        scheduler.add_job(run_sync, "cron", hour=23, minute=55)  # once per day
        print("[SyncScheduler] Scheduled nightly sync (23:55 UTC).")
    else:
        print(f"[SyncScheduler] Unknown SYNC_MODE={SYNC_MODE}, defaulting to hourly.")
        scheduler.add_job(run_sync, "cron", minute=0)

    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("[SyncScheduler] Shutting down…")

