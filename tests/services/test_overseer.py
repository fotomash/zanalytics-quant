"""Tests for the Overseer service Kafka integration."""

import json
from unittest.mock import Mock

import pytest

from importlib import import_module

overseer_main = import_module("services.overseer.main")
from agents.overseer_agent import OverseerAgent


class DummyConsumer:
    """Async iterator mimicking :class:`KafkaConsumer`."""

    def __init__(self, messages: list[str]):
        self._messages = messages

    async def __aenter__(self) -> "DummyConsumer":
        self._iter = iter(self._messages)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        pass

    def __aiter__(self) -> "DummyConsumer":
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._iter)
        except StopIteration:  # pragma: no cover - exhaust messages
            raise StopAsyncIteration


@pytest.mark.asyncio
async def test_overseer_creates_ticket(monkeypatch) -> None:
    """``run`` consumes events and dispatches incident tickets."""

    events = [
        json.dumps({"type": "error", "description": "boom", "code": 500}),
    ]
    dummy_consumer = DummyConsumer(events)
    monkeypatch.setattr(overseer_main, "KafkaConsumer", lambda *a, **k: dummy_consumer)

    mock_create = Mock()
    from agents import overseer_agent

    monkeypatch.setattr(overseer_agent.EnhancedTicketingSystem, "create_ticket", mock_create)

    agent = OverseerAgent(profile={})

    def fake_print(payload, *args, **kwargs):
        agent.process_system_event(payload)

    monkeypatch.setattr("builtins.print", fake_print)

    await overseer_main.run()

    mock_create.assert_called_once_with(
        {
            "type": "error",
            "description": "boom",
            "metadata": {"code": 500},
        }
    )
