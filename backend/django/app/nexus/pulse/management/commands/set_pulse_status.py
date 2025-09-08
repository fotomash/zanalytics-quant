from __future__ import annotations

import json
from django.core.management.base import BaseCommand

from app.nexus.views import _redis_client


class Command(BaseCommand):
    help = "Set or clear pulse_status Redis keys for demo purposes."

    def add_arguments(self, parser):
        parser.add_argument("symbol", help="e.g. XAUUSD")
        parser.add_argument("--set", dest="payload", help='JSON string, e.g. \"{"context":1,"liquidity":1}\"')
        parser.add_argument("--clear", action="store_true", help="Clear any cached/demo keys for this symbol")

    def handle(self, *args, **opts):
        sym = opts["symbol"]
        r = _redis_client()
        if r is None:
            self.stderr.write(self.style.ERROR("Redis unavailable"))
            return
        key_json = f"pulse_status:{sym}"
        key_demo = f"pulse_status:{sym}:demo"
        if opts.get("clear"):
            try:
                r.delete(key_json)
                r.delete(key_demo)
            except Exception:
                pass
            self.stdout.write(self.style.SUCCESS(f"Cleared {key_json} and {key_demo}"))
            return
        payload = opts.get("payload")
        if not payload:
            self.stderr.write(self.style.ERROR("Nothing to set. Provide --set '{...}' or --clear."))
            return
        try:
            obj = json.loads(payload)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Invalid JSON: {e}"))
            return
        try:
            r.setex(key_json, 30, json.dumps(obj))
            r.setex(key_demo, 300, json.dumps(obj))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Redis error: {e}"))
            return
        self.stdout.write(self.style.SUCCESS(f"Set demo status for {sym}: {obj}"))

