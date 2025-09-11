from typing import Any
from collections.abc import Iterable

TELEGRAM_MAX_LENGTH = 4096


def _to_lines(value: Any) -> str:
    """Convert lists or scalars to newline-delimited strings."""
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return "\n".join(f"- {item}" for item in value)
    return str(value)


def format_message(payload: dict) -> str:
    """Format a payload dict into a Telegram-ready Markdown string.

    Args:
        payload: Dictionary possibly containing symbol, score, reasons, warnings.

    Returns:
        str: Markdown formatted message within Telegram length limits.
    """
    symbol = payload.get("symbol") or payload.get("ticker") or "Unknown"
    parts = [f"*Symbol*: {symbol}"]

    score = payload.get("score")
    if score is not None:
        parts.append(f"*Score*: {score}")

    reasons = payload.get("reasons")
    if reasons:
        parts.append(f"*Reasons:*\n{_to_lines(reasons)}")

    warnings = payload.get("warnings")
    if warnings:
        parts.append(f"*Warnings:*\n_{_to_lines(warnings)}_")

    message = "\n".join(parts).strip()

    if len(message) > TELEGRAM_MAX_LENGTH:
        message = message[: TELEGRAM_MAX_LENGTH - 1] + "…"

    return message
