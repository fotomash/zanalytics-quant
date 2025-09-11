from typing import Any, Dict
from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Simple health check model with helper constructors."""

    service: str
    status: str
    details: Dict[str, Any] = {}

    @classmethod
    def healthy(cls, service: str, details: Dict[str, Any] | None = None) -> "HealthStatus":
        """Return a healthy status for ``service`` with optional ``details``."""
        return cls(service=service, status="healthy", details=details or {})
