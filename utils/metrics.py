from __future__ import annotations

"""Prometheus metrics helpers for processors."""

from functools import wraps

from prometheus_client import Counter, Summary

# Metrics -----------------------------------------------------------------
# Track processing time and total errors across all processors
process_time = Summary(
    "processor_process_time_seconds", "Time spent in processor functions"
)
error_count = Counter(
    "processor_error_count", "Number of errors raised by processor functions"
)


def record_metrics(func):
    """Decorator to measure processing time and count errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with process_time.time():
            try:
                return func(*args, **kwargs)
            except Exception:  # pragma: no cover - metrics only
                error_count.inc()
                raise

    return wrapper
