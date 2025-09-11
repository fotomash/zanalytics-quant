from ops.kafka import replay_consumer as rc


class DummyMessage:
    def __init__(self, value, err=None):
        self._value = value
        self._err = err

    def value(self):
        return self._value

    def error(self):
        return self._err


class FakeConsumer:
    def __init__(self, batches):
        self._batches = list(batches)

    def consume(self, batch_size, timeout):
        return self._batches.pop(0) if self._batches else []


def test_simple_print_mode(capfd):
    msgs = [DummyMessage(b"a"), DummyMessage(b"b")]
    consumer = FakeConsumer([msgs])
    rc.consume(consumer, 2, rc.print_messages)
    out = capfd.readouterr().out.splitlines()
    assert out == ["a", "b"]


def test_batch_sink_mode(capfd):
    msgs = [DummyMessage(b"a"), DummyMessage(b"b")]
    consumer = FakeConsumer([msgs])
    rc.consume(consumer, 2, rc.batch_sink)
    out = capfd.readouterr().out.strip()
    assert out == "Batch size: 2"
