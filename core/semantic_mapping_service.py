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


__all__ = ["SemanticMappingService"]
