from services import predict_cron


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.published = []

    def get(self, key):
        return self.store.get(key)

    def publish(self, channel, message):
        self.published.append((channel, message))


def test_no_alert_before_threshold(monkeypatch):
    r = FakeRedis()
    r.store[predict_cron.LAST_EVENT_KEY] = "100"
    monkeypatch.setattr(predict_cron.time, "time", lambda: 150)
    monkeypatch.setattr(predict_cron, "call_local_echo", lambda prompt: "ignored")

    predict_cron.check_silence(r, threshold=60)

    assert r.published == []


def test_alert_after_threshold(monkeypatch):
    r = FakeRedis()
    r.store[predict_cron.LAST_EVENT_KEY] = "0"
    captured = {}

    def fake_echo(prompt: str) -> str:
        captured["prompt"] = prompt
        return "alert"

    monkeypatch.setattr(predict_cron.time, "time", lambda: 100)
    monkeypatch.setattr(predict_cron, "call_local_echo", fake_echo)

    predict_cron.check_silence(r, threshold=60)

    assert r.published == [(predict_cron.ALERT_CHANNEL, "alert")]
    assert captured["prompt"] == "No predictions for 100s"
