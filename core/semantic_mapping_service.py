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
