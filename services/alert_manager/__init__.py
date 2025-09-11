"""Alert manager service.

Provides a minimal API for emitting alerts that can be expanded by
future integrations.  A module-level ``send_alert`` helper uses a
singleton ``AlertManager`` instance for convenience.
"""
"""Alert manager service providing a simple dispatch API."""

from .manager import Alert, AlertManager

_default_manager = AlertManager()


def send_alert(alert: Alert):
    """Send ``alert`` using the default :class:`AlertManager` instance."""
    return _default_manager.send_alert(alert)


__all__ = ["Alert", "AlertManager", "send_alert"]
"""Alert manager service package."""
