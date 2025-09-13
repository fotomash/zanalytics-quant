"""Utility functions for alerting.

This module integrates with basic notification providers (email, Slack,
generic webhooks) to deliver alerts. Providers are configured via
environment variables and each delivery attempt is retried to improve
reliability. Failures are logged for observability.
"""

from __future__ import annotations

import os
import smtplib
import time
from email.message import EmailMessage
from typing import Callable, Iterable, Tuple

import requests

from services.common import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 1  # seconds


def _with_retries(action: Callable[[], None], provider: str) -> None:
    """Execute ``action`` with retries and log failures."""

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            action()
            logger.info("Alert sent via %s", provider)
            return
        except Exception as exc:  # pragma: no cover - defensive
            if attempt == _MAX_RETRIES:
                logger.exception(
                    "Failed to send alert via %s after %s attempts: %s",
                    provider,
                    _MAX_RETRIES,
                    exc,
                )
            else:
                logger.warning(
                    "Attempt %s/%s to send alert via %s failed: %s",
                    attempt,
                    _MAX_RETRIES,
                    provider,
                    exc,
                )
                time.sleep(_RETRY_DELAY)


def _send_slack(service_name: str, error_message: str, url: str) -> None:
    payload = {"text": f"[{service_name}] {error_message}"}
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()


def _send_webhook(service_name: str, error_message: str, url: str) -> None:
    payload = {"service": service_name, "error": error_message}
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()


def _send_email(service_name: str, error_message: str, config: dict[str, str]) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"Alert: {service_name}"
    msg["From"] = config["from"]
    msg["To"] = config["to"]
    msg.set_content(error_message)

    with smtplib.SMTP(config["host"], config.get("port", 25), timeout=10) as smtp:
        if config.get("username") and config.get("password"):
            smtp.starttls()
            smtp.login(config["username"], config["password"])
        smtp.send_message(msg)


def send_alert(service_name: str, error_message: str) -> None:
    """Send an alert via configured providers.

    Providers are selected based on environment variables:

    - ``ALERT_SLACK_WEBHOOK_URL`` – Slack incoming webhook URL
    - ``ALERT_WEBHOOK_URL`` – generic webhook URL
    - ``ALERT_EMAIL_TO``/``ALERT_EMAIL_FROM``/``ALERT_SMTP_HOST`` – email
      configuration (optional ``ALERT_SMTP_PORT``, ``ALERT_SMTP_USERNAME``,
      ``ALERT_SMTP_PASSWORD``)
    """

    providers: Iterable[Tuple[str, Callable[[], None]]] = []

    slack_url = os.getenv("ALERT_SLACK_WEBHOOK_URL")
    if slack_url:
        providers = [
            *providers,
            ("slack", lambda: _send_slack(service_name, error_message, slack_url)),
        ]

    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        providers = [
            *providers,
            ("webhook", lambda: _send_webhook(service_name, error_message, webhook_url)),
        ]

    email_to = os.getenv("ALERT_EMAIL_TO")
    email_from = os.getenv("ALERT_EMAIL_FROM")
    smtp_host = os.getenv("ALERT_SMTP_HOST")
    if email_to and email_from and smtp_host:
        config = {
            "to": email_to,
            "from": email_from,
            "host": smtp_host,
            "port": int(os.getenv("ALERT_SMTP_PORT", "25")),
            "username": os.getenv("ALERT_SMTP_USERNAME", ""),
            "password": os.getenv("ALERT_SMTP_PASSWORD", ""),
        }
        providers = [
            *providers,
            ("email", lambda: _send_email(service_name, error_message, config)),
        ]

    if not providers:
        logger.warning("No alert providers configured; alert not sent for %s", service_name)
        return

    for name, action in providers:
        _with_retries(action, name)


__all__ = ["send_alert"]

