import importlib.util
from pathlib import Path
from datetime import datetime
import pytest

# Dynamically load the script module since "scripts" isn't a package
spec = importlib.util.spec_from_file_location(
    "predict_cron", Path(__file__).resolve().parents[1] / "scripts" / "predict_cron.py"
)
predict_cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(predict_cron)


class _FixedDatetime(datetime):
    _now = datetime(2024, 1, 1, 12, 0, 0)

    @classmethod
    def utcnow(cls):
        return cls._now


def test_compute_silence_duration_iso(monkeypatch):
    _FixedDatetime._now = datetime(2024, 1, 1, 12, 0, 0)
    monkeypatch.setattr(predict_cron, "datetime", _FixedDatetime)
    ts = "2024-01-01T11:59:00Z"
    assert predict_cron.compute_silence_duration(ts) == 60


def test_compute_silence_duration_epoch(monkeypatch):
    _FixedDatetime._now = datetime.utcfromtimestamp(100)
    monkeypatch.setattr(predict_cron, "datetime", _FixedDatetime)
    assert predict_cron.compute_silence_duration(40) == 60


def test_compute_silence_duration_bad(monkeypatch):
    _FixedDatetime._now = datetime(2024, 1, 1, 12, 0, 0)
    monkeypatch.setattr(predict_cron, "datetime", _FixedDatetime)
    with pytest.raises(ValueError):
        predict_cron.compute_silence_duration("not-a-timestamp")
