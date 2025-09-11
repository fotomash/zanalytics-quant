import logging

import pytest

from tick_to_bar_service import TickToBarService


def test_process_tick_logs_exception_with_metadata(caplog):
    service = TickToBarService()
    bad_tick = {"bid": "abc", "ask": "1.2", "volume": 0, "timestamp": "2023-01-01T00:00:00Z"}
    topic = "test-topic"
    key = "test-key"

    with caplog.at_level(logging.ERROR):
        service.process_tick("EURUSD", bad_tick, topic=topic, key=key)

    # Ensure an error was logged with stack trace and metadata
    assert any(record.exc_info for record in caplog.records)
    log_messages = "".join(record.getMessage() for record in caplog.records)
    assert topic in log_messages
    assert key in log_messages
    assert "'bid': 'abc'" in log_messages
