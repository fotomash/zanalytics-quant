#!/usr/bin/env python3
"""
Pulse → Telegram notifier (minimal, optional).

Reads recent gate-hit events from Redis and posts compact alerts to a
Telegram chat when confidence >= threshold. Safe no-op when config
is missing. Intended to be run as a sidecar/cron.

Env:
  REDIS_URL=redis://localhost:6379/0
  TELEGRAM_BOT_TOKEN=123:ABC
  TELEGRAM_CHAT_ID=-100123456789
  PULSE_TG_THRESHOLD=0.6              # 0..1
  PULSE_TG_SYMBOLS=ALL or CSV (e.g. "XAUUSD,EURUSD")
  PULSE_TG_MIN_INTERVAL_SEC=30        # per-symbol cooldown

Usage:
  python services/pulse_telegram_worker.py        # one iteration
  WATCH=1 python services/pulse_telegram_worker.py  # simple loop
"""
from __future__ import annotations

import os
import time
import json
from typing import Dict, Any, List, Optional

import redis
import requests


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _connect_redis() -> Optional[redis.Redis]:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        return redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def _should_send(ev: Dict[str, Any], *, thr: float, allow_syms: Optional[List[str]], r: redis.Redis) -> bool:
    try:
        sym = str(ev.get("symbol") or "").upper()
        score = float(ev.get("score") or 0.0)
        passed = bool(ev.get("passed"))
        if allow_syms and sym and sym not in allow_syms:
            return False
        if not passed:
            return False
        return score >= thr
    except Exception:
        return False


def _dedupe_key(ev: Dict[str, Any]) -> str:
    return f"{ev.get('symbol')}|{ev.get('gate')}|{int(float(ev.get('score') or 0.0)*100)}"


def _cooldown_ok(sym: str, r: redis.Redis, min_interval: int) -> bool:
    if not sym:
        return True
    key = f"pulse:tg:last:{sym}"
    try:
        last = r.get(key)
        now = int(time.time())
        if last and (now - int(last)) < min_interval:
            return False
        r.setex(key, max(60, min_interval), str(now))
        return True
    except Exception:
        return True


def _send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=3.0,
        )
        return bool(resp.ok)
    except Exception:
        return False


def run_once() -> int:
    r = _connect_redis()
    if r is None:
        return 0
    threshold = _env_float("PULSE_TG_THRESHOLD", 0.6)
    allow_csv = os.getenv("PULSE_TG_SYMBOLS", "ALL")
    allow_syms = None if allow_csv.upper() == "ALL" else [s.strip().upper() for s in allow_csv.split(",") if s.strip()]
    min_interval = _env_int("PULSE_TG_MIN_INTERVAL_SEC", 30)

    n_sent = 0
    try:
        raw_list = r.lrange("pulse:gate_hits", -200, -1) or []
        for raw in raw_list[-50:]:  # last 50 events
            try:
                ev = json.loads(raw)
            except Exception:
                continue
            if not _should_send(ev, thr=threshold, allow_syms=allow_syms, r=r):
                continue
            sym = str(ev.get("symbol") or "").upper()
            if not _cooldown_ok(sym, r, min_interval):
                continue
            ded = _dedupe_key(ev)
            if r.sismember("pulse:tg:dedupe", ded):
                continue
            text = (
                f"<b>PULSE</b> {sym} — gate <b>{ev.get('gate')}</b> PASSED\n"
                f"Confidence: {float(ev.get('score') or 0.0)*100:.0f}%"
            )
            if _send_telegram(text):
                n_sent += 1
                try:
                    r.sadd("pulse:tg:dedupe", ded)
                    r.expire("pulse:tg:dedupe", 3600)
                except Exception:
                    pass
    except Exception:
        return n_sent
    return n_sent


if __name__ == "__main__":
    if os.getenv("WATCH"):
        while True:
            try:
                run_once()
            except Exception:
                pass
            time.sleep(_env_int("PULSE_TG_POLL_SEC", 5))
    else:
        cnt = run_once()
        print(f"sent={cnt}")

