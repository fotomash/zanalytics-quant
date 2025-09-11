"""Alert manager service.

Provides a minimal API for emitting alerts that can be expanded by
future integrations.  A module-level ``send_alert`` helper uses a
singleton ``AlertManager`` instance for convenience.
"""

from .manager import Alert, AlertManager

_default_manager = AlertManager()


def send_alert(alert: Alert) -> dict:
    """Send ``alert`` using the default :class:`AlertManager` instance."""
    return _default_manager.send_alert(alert)


__all__ = ["Alert", "AlertManager", "send_alert"]
