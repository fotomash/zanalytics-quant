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

