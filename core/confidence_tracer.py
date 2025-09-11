"""Utilities for extracting confidence scores from agent results.

This module provides a very small, test friendly ``ConfidenceTracer``
class.  Real systems may implement complex logic or logging; here we
simply attempt to retrieve a ``confidence`` field from the result object
and normalise it to a ``float``.
"""
from __future__ import annotations

from typing import Any


class ConfidenceTracer:
    """Derive a numeric confidence score from agent output.

    The tracer expects the ``result`` produced by an agent to either be a
    mapping containing a ``"confidence"`` key or any object with a
    ``confidence`` attribute.  If the field is missing or cannot be
    coerced to ``float`` a score of ``0.0`` is returned.  This lenient
    behaviour keeps the tracer lightweight and suitable for tests where
    only basic scoring is required.
    """

    field_name = "confidence"

    def trace(self, result: Any) -> float:
        """Return a confidence score for ``result``.

        Parameters
        ----------
        result:
            Arbitrary object produced by an agent.

        Returns
        -------
        float
            Extracted confidence in the range ``0.0``–``1.0`` where
            ``0.0`` indicates unknown/low confidence.
        """

        if result is None:
            return 0.0

        # Support dictionary‑like objects
        if isinstance(result, dict):
            value = result.get(self.field_name)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0

        # Support attribute access
        value = getattr(result, self.field_name, None)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        return 0.0


__all__ = ["ConfidenceTracer"]
