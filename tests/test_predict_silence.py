import importlib.util
from pathlib import Path
import time

# Load scripts/predict_cron.py as a module
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "predict_cron_script", ROOT / "scripts" / "predict_cron.py"
)
predict_cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(predict_cron)


def test_compute_silence_duration_accepts_str_and_numeric():
    now = time.time()
    numeric = predict_cron.compute_silence_duration(now - 10)
    assert 9 <= numeric <= 11
    string = predict_cron.compute_silence_duration(str(now - 10))
    assert 9 <= string <= 11


def test_predict_silence_decodes_bytes(monkeypatch):
    class DummyRedis:
        def __init__(self, value):
            self.value = value

        def get(self, key):
            return self.value

    now = time.time()
    dummy = DummyRedis(str(now - 5).encode())
    monkeypatch.setattr(predict_cron.time, "time", lambda: now)
    assert predict_cron.predict_silence(dummy) == 5
