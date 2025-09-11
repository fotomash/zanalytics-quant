"""Abstractions for agent memory storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AgentMemoryInterface(ABC):
    """Interface for memory backends used by agents.

    Implementations are responsible for persisting and retrieving
    memory items for a given agent identifier.
    """

    @abstractmethod
    def save(self, agent_id: str, memory: Dict[str, Any]) -> None:
        """Persist a single memory item for an agent."""

    @abstractmethod
    def load(self, agent_id: str) -> List[Dict[str, Any]]:
        """Return an ordered collection of memory items for ``agent_id``."""

    @abstractmethod
    def clear(self, agent_id: str) -> None:
        """Remove all stored memory for ``agent_id``."""


__all__ = ["AgentMemoryInterface"]
