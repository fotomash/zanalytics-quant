"""Shared logging utilities for services.

This module exposes helper functions to configure the standard
``logging`` module with a consistent format and log level across all
services. Individual services should obtain a logger via
``get_logger(__name__)`` and use it instead of ``print`` statements.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: Optional[str] = None) -> None:
    """Configure root logging.

    Parameters
    ----------
    level:
        Optional log level name. If not provided, the ``LOG_LEVEL``
        environment variable is consulted and defaults to ``INFO``.
    """

    level_name = level or os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.basicConfig(level=log_level, format=_LOG_FORMAT, stream=sys.stdout)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with global configuration applied."""

    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger"]

