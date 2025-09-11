"""Alert management functionality."""


def send_alert(service_name: str, error_message: str) -> None:
    """Print a stub alert message and raise an implementation error.

    Args:
        service_name: Name of the service emitting the alert.
        error_message: Description of the error to report.

    Raises:
        NotImplementedError: Always, since alerting is not yet implemented.
    """
    print("--- ALERT STUB ---")
    print(f"SERVICE: {service_name}")
    print(f"ERROR: {error_message}")
    print("--------------------")
    raise NotImplementedError(
        "Alerting functionality is planned but not yet implemented."
    )
