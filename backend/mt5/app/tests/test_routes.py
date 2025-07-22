import types
import sys
import os

class DummyMT5(types.ModuleType):
    def __getattr__(self, name):
        return 0

sys.modules['MetaTrader5'] = DummyMT5('MetaTrader5')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pytest

from app import app
from routes import data

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_get_ticks(client, monkeypatch):
    sample = [
        {'time': 1000, 'bid': 1.1, 'ask': 1.2, 'last': 1.15, 'volume': 10},
        {'time': 1001, 'bid': 1.11, 'ask': 1.21, 'last': 1.16, 'volume': 12},
    ]

    def fake_copy_ticks_from(symbol, start, limit, flag):
        return sample

    monkeypatch.setattr(data.mt5, 'copy_ticks_from', fake_copy_ticks_from)

    resp = client.get('/ticks?symbol=EURUSD&limit=2')
    assert resp.status_code == 200
    data_resp = resp.get_json()
    assert len(data_resp) == 2
    assert data_resp[0]['bid'] == 1.1

def test_get_bars(client, monkeypatch):
    sample = [
        {'time': 1000, 'open': 1.0, 'high': 1.2, 'low': 0.9, 'close': 1.1, 'tick_volume': 10, 'spread': 2, 'real_volume': 15},
        {'time': 1001, 'open': 1.1, 'high': 1.3, 'low': 1.0, 'close': 1.2, 'tick_volume': 12, 'spread': 2, 'real_volume': 16},
    ]

    def fake_copy_rates_from_pos(symbol, timeframe, pos, limit):
        return sample

    monkeypatch.setattr(data.mt5, 'copy_rates_from_pos', fake_copy_rates_from_pos)
    monkeypatch.setattr(data, 'get_timeframe', lambda tf: 1)

    resp = client.get('/bars/EURUSD/M1?limit=2')
    assert resp.status_code == 200
    data_resp = resp.get_json()
    assert len(data_resp) == 2
    assert data_resp[0]['open'] == 1.0
