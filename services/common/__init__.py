"""Common utilities for services.

This package exposes shared helpers used across the various service
implementations. The ``logging_utils`` module provides a convenience
``get_logger`` function for consistent logging configuration.
"""

from .logging_utils import get_logger, configure_logging

__all__ = ["get_logger", "configure_logging"]

