"""Overseer agent for system-wide monitoring and incident logging."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from multi_agent_memory_integration import MultiAgentMemory
from ticketing_system import TicketingSystem
from services.vectorization_service.brown_vector_store_integration import (
    BrownVectorPipeline,
)

logger = logging.getLogger(__name__)


class OverseerAgent:
    """Agent responsible for processing system events."""

    def __init__(self, profile: Dict[str, Any]) -> None:
        """Initialize the agent using the supplied profile."""

        self.profile = profile
        self.ticketing: TicketingSystem | None = self._init_integration(TicketingSystem)
        self.memory: MultiAgentMemory | None = self._init_integration(MultiAgentMemory)
        self.vector_store: BrownVectorPipeline | None = self._init_integration(
            BrownVectorPipeline
        )

    def _init_integration(self, cls):
        """Instantiate an integration with basic error handling."""
        try:
            return cls()
        except Exception as exc:  # pragma: no cover - network/config dependent
            logger.warning("%s unavailable: %s", cls.__name__, exc)
            return None

    def _retry(self, func, *args, retries: int = 3, **kwargs):
        """Call ``func`` with simple retry logic."""
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - integration specific
                if attempt == retries - 1:
                    logger.error("%s failed after %d attempts: %s", func.__name__, retries, exc)
                else:
                    time.sleep(1)

    def process_system_event(self, event: Dict[str, Any]) -> None:
        """Handle a system event and create a structured incident ticket."""
        history = []
        if self.memory:
            history = self._retry(self.memory.fetch, "overseer") or []
        payload = {
            "type": event.get("type", "system_event"),
            "description": event.get("description", ""),
            "metadata": {
                k: v for k, v in event.items() if k not in {"type", "description"}
            },
            "history": history,
        }
        if self.ticketing:
            self._retry(self.ticketing.create_ticket, payload)
        if self.memory:
            self._retry(self.memory.store, "overseer", payload)
        if self.vector_store:
            self._retry(
                self.vector_store.upsert_vector,
                str(time.time()),
                [],
                {"type": payload["type"]},
            )


__all__ = ["OverseerAgent"]
