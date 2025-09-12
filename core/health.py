from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict


@dataclass
class HealthStatus:
    """Represents the health of a service and its dependencies."""

    service_name: str
    status: str
    timestamp: str
    dependencies: Dict[str, str]

    @classmethod
    def healthy(cls, service_name: str, deps: Dict[str, bool]) -> "HealthStatus":
        """Construct a healthy status, mapping dependency checks to strings."""
        return cls(
            service_name=service_name,
            status="healthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            dependencies={
                name: "connected" if ok else "unreachable" for name, ok in deps.items()
            },
        )

    @classmethod
    def unhealthy(cls, service_name: str, deps: Dict[str, bool]) -> "HealthStatus":
        """Construct an unhealthy status, mapping dependency checks to strings."""
        return cls(
            service_name=service_name,
            status="unhealthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            dependencies={
                name: "connected" if ok else "unreachable" for name, ok in deps.items()
            },
        )

    def to_dict(self) -> Dict[str, str]:
        """Return a JSON-serializable representation."""
        return {
            "service_name": self.service_name,
            "status": self.status,
            "timestamp": self.timestamp,
            "dependencies": self.dependencies,
        }
