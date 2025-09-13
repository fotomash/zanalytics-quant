import json
import sqlite3
from types import SimpleNamespace

import core.journal_sync as js


def test_write_journal_entry_sqlite(tmp_path, monkeypatch):
    """Entries should persist to SQLite when configured."""

    db_path = tmp_path / "journal.db"
    monkeypatch.setenv("JOURNAL_BACKEND", "sqlite")
    monkeypatch.setenv("JOURNAL_DB_PATH", str(db_path))

    entry = {"ticket": 1, "symbol": "EURUSD"}
    js.write_journal_entry(entry)

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT data FROM journal").fetchone()
    finally:
        conn.close()
    assert json.loads(row[0]) == entry


def test_write_journal_entry_redis_errors_handled(monkeypatch):
    """Redis backend errors should not propagate."""

    monkeypatch.setenv("JOURNAL_BACKEND", "redis")

    class DummyClient:
        def xadd(self, *a, **k):  # pragma: no cover - executed
            raise RuntimeError("boom")

    monkeypatch.setattr(
        js, "redis", SimpleNamespace(from_url=lambda *a, **k: DummyClient())
    )

    # Should not raise despite the xadd failure
    js.write_journal_entry({"ticket": 2})


def test_detect_behavior_flags_excessive_volume():
    """Large trade volume should trigger an EXCESSIVE_VOLUME flag."""

    js._LAST_DEAL_BY_SYMBOL.clear()
    deal = SimpleNamespace(symbol="EURUSD", type=0, time=100, volume=10)
    flags = js.detect_behavior_flags(deal)
    assert "EXCESSIVE_VOLUME" in flags


def test_detect_behavior_flags_rapid_flip():
    """Opposite trades within the rapid flip window should be flagged."""

    js._LAST_DEAL_BY_SYMBOL.clear()
    first = SimpleNamespace(symbol="EURUSD", type=0, time=100, volume=1)
    second = SimpleNamespace(symbol="EURUSD", type=1, time=120, volume=1)

    js.detect_behavior_flags(first)
    flags = js.detect_behavior_flags(second)

    assert "RAPID_FLIP" in flags

