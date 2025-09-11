"""Utility functions for alerting.

This module currently exposes a stub implementation for sending alerts. A
future iteration will integrate with the project's preferred notification
system.
"""


def send_alert(service_name: str, error_message: str) -> None:
    """Print a placeholder alert and raise ``NotImplementedError``.

    Parameters
    ----------
    service_name:
        Name of the service emitting the alert.
    error_message:
        Details about the error condition.

    Raises
    ------
    NotImplementedError
        Always raised because the real alerting system is not yet
        implemented.
    """
    print("--- ALERT STUB ---")
    print(f"SERVICE: {service_name}")
    print(f"ERROR: {error_message}")
    print("--------------------")
    raise NotImplementedError(
        "Alerting functionality is planned but not yet implemented."
    )
