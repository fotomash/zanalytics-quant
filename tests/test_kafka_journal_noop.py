from backend.django.app.nexus.pulse.journal.kafka_journal import (
    KafkaJournalEngine,
    example_envelope,
)


def test_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("USE_KAFKA_JOURNAL", "false")
    eng = KafkaJournalEngine()
    assert eng.enabled is False
    eng.emit(example_envelope("XAUUSD", 0.5))
    eng.flush()


def test_noop_when_lib_missing(monkeypatch):
    monkeypatch.setenv("USE_KAFKA_JOURNAL", "true")
    eng = KafkaJournalEngine(brokers="invalid:1234")
    eng.emit(example_envelope("EURUSD", 0.7))
    eng.flush()
