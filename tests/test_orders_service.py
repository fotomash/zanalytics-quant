from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "django"))
app_stub = types.ModuleType("app")
app_stub.__path__ = [str(ROOT / "backend" / "django" / "app")]
sys.modules.setdefault("app", app_stub)

os.environ.setdefault("MT5_URL", "http://dummy")

from app.nexus import orders_service


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def clear_cache():
    orders_service._SYMBOL_META_CACHE.clear()  # type: ignore[attr-defined]


def test_normalize_volume_step_001():
    clear_cache()
    meta = {"volume_step": 0.01, "volume_min": 0.01, "volume_max": 100.0}
    with patch("app.nexus.orders_service.requests.get", return_value=DummyResponse(meta)) as mock_get:
        assert orders_service._normalize_volume("EURUSD", 0.027) == 0.02
        assert orders_service._normalize_volume("EURUSD", 0.003) == 0.01
        # second call hits cache
        assert mock_get.call_count == 1


def test_normalize_volume_step_05():
    clear_cache()
    meta = {"volume_step": 0.5, "volume_min": 1.0, "volume_max": 2.5}
    with patch("app.nexus.orders_service.requests.get", return_value=DummyResponse(meta)) as mock_get:
        assert orders_service._normalize_volume("XAUUSD", 1.76) == 1.5
        assert orders_service._normalize_volume("XAUUSD", 0.1) == 1.0
        assert orders_service._normalize_volume("XAUUSD", 4.0) == 2.5
        assert mock_get.call_count == 1

