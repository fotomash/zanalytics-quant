"""Simple ticketing system integration stub.

This module exposes :class:`TicketingSystem`, a minimal interface used by
agents to file incident reports.  The implementation is intentionally light
weight and suitable for unit testing.  In a production deployment this would
bridge to an external service such as JIRA or ServiceNow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TicketingSystem:
    """Placeholder ticketing system client with a stable API."""

    def create_ticket(self, payload: Dict[str, Any]) -> None:  # pragma: no cover - side effect only
        """Submit an incident ticket.

        Parameters
        ----------
        payload:
            Structured incident description.
        """
        # A real implementation would dispatch the payload to an external system.
        logger.info("Ticket created: %s", payload)


__all__ = ["TicketingSystem"]
