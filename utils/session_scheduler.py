import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from apscheduler.schedulers.background import BackgroundScheduler
import requests
import yaml

# Orchestrator endpoint that understands the flow 'session_close_debrief'.
# This is intentionally separate from the Django API to keep layers clean.
API_ORCHESTRATOR_URL = os.getenv("API_ORCHESTRATOR_URL", "https://your-orchestrator-host")
API_TOKEN = os.getenv("API_TOKEN", "")
SESSION_TIMES_FILE = os.getenv("SESSION_TIMES_FILE", "docs/gpt_llm/session_times.yaml")
HEALTH_PORT = int(os.getenv("SESSION_SCHEDULER_PORT", "8011"))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_session_times():
    """Load session close times from YAML config.

    Example YAML:
      London: { hour: 16, minute: 30 }
      NewYork: { hour: 21, minute: 0 }
    """
    try:
        with open(SESSION_TIMES_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if isinstance(data, dict) and data:
                return data
    except Exception as e:
        print("[Scheduler] Could not load session times; using defaults.", e)
    return {
        "London": {"hour": 16, "minute": 30},
        "NewYork": {"hour": 21, "minute": 0},
    }


def run_session_close_debrief(session_name: str):
    """Trigger orchestrator flow 'session_close_debrief' for a named session.

    The orchestrator is expected to run the prompt flow and optionally write a journal entry.
    """
    print(f"[Scheduler] Running {session_name} session close debrief...")

    try:
        headers = {"Content-Type": "application/json"}
        if API_TOKEN:
            headers["Authorization"] = f"Bearer {API_TOKEN}"
        payload = {"type": "session_close_debrief", "payload": {"session": session_name}}
        url = f"{API_ORCHESTRATOR_URL.rstrip('/')}/api/v1/actions/query"
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        data = resp.json() if resp.ok else {"ok": False, "status": resp.status_code}
        print(f"[Scheduler] {session_name} Debrief result:", data)
    except Exception as e:
        print(f"[Scheduler] Error running {session_name} debrief:", e)


def _start_health_server(scheduler):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
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
    logger.info("[Scheduler] Health server started on port %s", HEALTH_PORT)


def start_scheduler():
    scheduler = BackgroundScheduler()
    session_times = load_session_times()

    for session_name, cfg in session_times.items():
        hour = int(cfg.get("hour", 0))
        minute = int(cfg.get("minute", 0))
        scheduler.add_job(
            run_session_close_debrief,
            "cron",
            args=[session_name],
            hour=hour,
            minute=minute,
        )
        print(f"[Scheduler] Scheduled {session_name} close at {hour:02d}:{minute:02d} UTC")

    _start_health_server(scheduler)

    try:
        scheduler.start()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Scheduler] Failed to start scheduler: %s", exc)
        try:
            scheduler.shutdown(wait=False)
        except Exception:  # pragma: no cover
            logger.exception("[Scheduler] Error during scheduler shutdown")
        time.sleep(5)
        logger.info("[Scheduler] Retrying scheduler start…")
        scheduler.start()

    print("[Scheduler] Session close debrief jobs scheduled.")
    return scheduler


if __name__ == "__main__":
    scheduler = start_scheduler()
    # Keep process alive
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("[Scheduler] Shutting down...")
        scheduler.shutdown(wait=False)

