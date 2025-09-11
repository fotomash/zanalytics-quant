from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


class SemanticMappingService:
    """Resolve tasks to their primary and fallback agents.

    The service maintains a simple mapping between a task identifier and
    the agent that should handle it.  Tasks are expected to be ``dict``
    objects containing at least a ``name``/``type``/``task`` key.  The
    mapping returns a tuple consisting of the primary agent identifier and
    a list of fallback agent identifiers.
    """

    def __init__(
        self,
        mapping: Optional[Dict[str, Tuple[str, List[str]]]] = None,
    ) -> None:
        self.mapping: Dict[str, Tuple[str, List[str]]] = mapping or {}

    def route(self, task: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
        """Return the primary agent and fallbacks for ``task``.

        Parameters
        ----------
        task:
            Arbitrary task description.  The service attempts to extract a
            task identifier from the ``name``, ``type`` or ``task`` fields.

        Returns
        -------
        tuple
            ``(primary, fallbacks)`` where ``primary`` may be ``None`` when
            no mapping exists.
        """

        task_id = (
            task.get("name")
            or task.get("type")
            or task.get("task")
        )
        if task_id is None:
            return None, []
        primary, fallbacks = self.mapping.get(task_id, (None, []))
        return primary, list(fallbacks)

"""Simple semantic routing utilities.

The real project contains a service responsible for determining which
fallback agents should handle a request when the primary agent's
confidence score is insufficient.  For the purposes of the unit tests in
this kata the service provides a minimal stub with a single ``route``
method that may be monkey‑patched by tests.
"""
from __future__ import annotations

from typing import List


class SemanticMappingService:
    """Return fallback agent identifiers for a given primary agent."""

    @staticmethod
    def route(agent_id: str) -> List[str]:  # pragma: no cover - trivial
        """Return an ordered list of fallback agent identifiers.

        The default implementation returns an empty list.  Unit tests
        typically patch this method to supply custom routing behaviour.
        """

        return []


__all__ = ["SemanticMappingService"]
