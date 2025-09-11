import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import services.persistence.consumer as mod


class DummyMsg:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def value(self) -> bytes:
        return self._payload

    def error(self):  # pragma: no cover - simple stub
        return None


class DummyConsumer:
    def __init__(self, messages):
        self._iter = iter(messages + [None])

    def poll(self, timeout):
        return next(self._iter)


def _mock_connect(monkeypatch):
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()
    monkeypatch.setattr(
        mod, "psycopg2", SimpleNamespace(connect=lambda dsn: conn)
    )
    return conn


def test_replay_closes_connection(monkeypatch):
    conn = _mock_connect(monkeypatch)
    consumer = DummyConsumer([])
    monkeypatch.setattr(mod, "_write_batch", MagicMock())

    mod.replay_to_postgres(consumer)

    assert conn.close.called


def test_replay_flushes_final_batch(monkeypatch):
    messages = [
        DummyMsg(b"{}"),
        DummyMsg(b"{}"),
        DummyMsg(b"{}"),
    ]
    consumer = DummyConsumer(messages)
    conn = _mock_connect(monkeypatch)
    batches = []
    monkeypatch.setattr(mod, "_write_batch", lambda cur, batch: batches.append(list(batch)))

    mod.replay_to_postgres(consumer, batch_size=2)

    assert conn.close.called
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1

