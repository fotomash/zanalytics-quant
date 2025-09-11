import pytest
from unittest.mock import MagicMock

import utils.mt5_ingest as mt5_ingest


def _raise_runtime_error(*args, **kwargs):
    raise RuntimeError("boom")


def test_producer_closed_on_stream_exception(monkeypatch):
    mock_producer = MagicMock()
    mock_producer.producer.len.return_value = 0

    monkeypatch.setattr(mt5_ingest, "_get_producer", lambda: mock_producer)
    monkeypatch.setattr(mt5_ingest, "get_tick_from_mt5", _raise_runtime_error)

    with pytest.raises(RuntimeError):
        mt5_ingest.pull_and_stream()

    assert mock_producer.flush.called
    assert mock_producer.close.called


def test_producer_closed_on_flush_exception(monkeypatch):
    mock_producer = MagicMock()
    mock_producer.producer.len.return_value = 0
    mock_producer.flush.side_effect = ValueError("flush fail")

    monkeypatch.setattr(mt5_ingest, "_get_producer", lambda: mock_producer)
    monkeypatch.setattr(mt5_ingest, "get_tick_from_mt5", _raise_runtime_error)

    with pytest.raises(ValueError):
        mt5_ingest.pull_and_stream()

    assert mock_producer.close.called
