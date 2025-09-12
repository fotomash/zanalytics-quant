"""Utility functions for alerting.

This module currently exposes a stub implementation that simply logs an
alert and raises ``NotImplementedError``. A future iteration will
integrate with the project's notification system.
"""

from services.common import get_logger

logger = get_logger(__name__)


def send_alert(service_name: str, error_message: str) -> None:
    """Log a stub alert message and raise an implementation error."""

    logger.error("ALERT STUB - SERVICE: %s ERROR: %s", service_name, error_message)
    raise NotImplementedError(
        "Alerting functionality is planned but not yet implemented."
    )


__all__ = ["send_alert"]

