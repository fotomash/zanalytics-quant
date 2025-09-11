from datetime import datetime

from tick_to_bar_service import TickToBarService


class FakeRedis:
    """Minimal Redis-like interface for testing"""

    def __init__(self):
        self.hashes = {}
        self.streams = {}

    def hset(self, key, mapping):
        self.hashes[key] = mapping

    def hgetall(self, key):
        return self.hashes.get(key, {})

    def expire(self, key, seconds):
        pass

    def xadd(self, key, fields, maxlen=None):
        self.streams.setdefault(key, []).append(fields)
        return f"{len(self.streams[key])}-0"

    def publish(self, channel, message):
        pass

    def ping(self):
        return True


def test_process_tick_multiple_timeframes():
    service = TickToBarService()
    service.redis_client = FakeRedis()

    # Limit to 1m and 5m timeframes
    service.timeframes = {"1m": 60, "5m": 300}

    tick = {
        "bid": 1.0,
        "ask": 1.2,
        "volume": 100,
        "timestamp": datetime(2023, 1, 1, 0, 0, 0).isoformat(),
    }

    service.process_tick("EURUSD", tick)

    assert "stream:bar:1m:EURUSD" in service.redis_client.streams
    assert "stream:bar:5m:EURUSD" in service.redis_client.streams
