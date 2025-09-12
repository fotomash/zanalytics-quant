import json

import services.persistence.consumer as pc


class DummyMessage:
    def __init__(self, payload):
        self._payload = payload

    def error(self):
        return None

    def value(self):
        return json.dumps(self._payload).encode("utf-8")


class DummyConsumer:
    def __init__(self, messages):
        self._messages = messages
        self.committed = False

    def consume(self, batch_size, timeout):
        msgs = self._messages
        self._messages = []
        return msgs

    def commit(self, msg):
        self.committed = True


class DummyCursor:
    def __init__(self):
        self.executed = []

    def executemany(self, query, records):
        self.executed.extend(records)


class DummyConn:
    def __init__(self):
        self.cur = DummyCursor()
        self.committed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_process_batch_commits_offsets(monkeypatch):
    msg = DummyMessage({"timestamp": 0, "symbol": "EURUSD"})
    consumer = DummyConsumer([msg])
    conn = DummyConn()
    cursor = conn.cursor()

    monkeypatch.setattr(pc, "Json", lambda x: x)

    pc.process_batch(consumer, cursor, conn, batch_size=1)

    assert consumer.committed is True
    assert conn.committed is True
    assert cursor.executed
