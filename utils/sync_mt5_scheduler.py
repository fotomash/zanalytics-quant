import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from apscheduler.schedulers.background import BackgroundScheduler
from utils.sync_mt5_trades import fetch_mt5_trades, persist_trades


SYNC_MODE = os.getenv("SYNC_MODE", "hourly").lower()  # "hourly" or "nightly"
DATE_FROM = os.getenv("MT5_SYNC_FROM", "2025-09-01")
HEALTH_PORT = int(os.getenv("SCHEDULER_HEALTH_PORT", "8010"))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_sync():
    print("[SyncScheduler] Running MT5 → CSV trade export…")
    trades = fetch_mt5_trades(DATE_FROM)
    path = persist_trades(trades)
    print(f"[SyncScheduler] Exported {len(trades)} trades to {path}")


def _start_health_server(scheduler):
    """Expose a simple health endpoint reporting scheduler status."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (method name from BaseHTTPRequestHandler)
            if self.path == "/health":
                payload = json.dumps({"scheduler_running": scheduler.running})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload.encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):  # noqa: D401, N802
            return

    server = HTTPServer(("0.0.0.0", HEALTH_PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("[SyncScheduler] Health server started on port %s", HEALTH_PORT)


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

    _start_health_server(scheduler)

    try:
        scheduler.start()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[SyncScheduler] Failed to start scheduler: %s", exc)
        try:
            scheduler.shutdown(wait=False)
        except Exception:  # pragma: no cover - best effort shutdown
            logger.exception("[SyncScheduler] Error during scheduler shutdown")
        time.sleep(5)
        logger.info("[SyncScheduler] Retrying scheduler start…")
        scheduler.start()

    return scheduler


if __name__ == "__main__":
    scheduler = start_scheduler()
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("[SyncScheduler] Shutting down…")
        scheduler.shutdown(wait=False)

