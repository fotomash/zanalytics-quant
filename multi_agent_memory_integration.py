"""Lightweight multi-agent memory store.

The :class:`MultiAgentMemory` class offers a stable interface for persisting
and retrieving memories on a per-agent basis.  It is deliberately
in-memory and dependency free so that unit tests can exercise behaviour
without requiring external services.
"""

from __future__ import annotations

from typing import Any, Dict, List


class MultiAgentMemory:
    """Simple in-memory persistence layer for agent memories."""

    def __init__(self) -> None:
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def store(self, agent_id: str, item: Dict[str, Any]) -> None:
        """Persist an item for the given agent."""
        self._store.setdefault(agent_id, []).append(item)

    def fetch(self, agent_id: str) -> List[Dict[str, Any]]:
        """Retrieve the stored history for an agent."""
        return list(self._store.get(agent_id, []))


__all__ = ["MultiAgentMemory"]
