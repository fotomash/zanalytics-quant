import logging

from utils import accumulator
import pyarrow.parquet as pq


def test_flush_and_aggregate_no_ticks(monkeypatch, caplog):
    calls = {}

    def fake_write_table(table, file):
        calls["write"] = True

    def fake_log_event(event):
        calls["log"] = True

    monkeypatch.setattr(pq, "write_table", fake_write_table)
    monkeypatch.setattr(accumulator, "log_event", fake_log_event)

    caplog.set_level(logging.DEBUG)
    result = accumulator.flush_and_aggregate.run("EURUSD", [])

    assert result == {"status": "skipped", "reason": "no data"}
    assert "No ticks to process" in caplog.text
    assert calls == {}
