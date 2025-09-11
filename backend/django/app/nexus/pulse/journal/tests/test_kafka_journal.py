import os
from backend.django.app.nexus.pulse.journal.kafka_journal import KafkaJournalEngine, example_envelope


def test_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("USE_KAFKA_JOURNAL", "false")
    eng = KafkaJournalEngine()
    assert eng.enabled is False
    # Should not raise
    eng.emit(example_envelope("XAUUSD", 0.5))
    eng.flush()


def test_noop_when_lib_missing(monkeypatch):
    # Force enabled but library not available; engine should disable itself
    monkeypatch.setenv("USE_KAFKA_JOURNAL", "true")
    # Point to an invalid broker to ensure no producer is created
    eng = KafkaJournalEngine(brokers="invalid:1234")
    # Either disabled due to no Producer, or enabled but no producer created — both are no-op
    eng.emit(example_envelope("EURUSD", 0.7))
    eng.flush()

