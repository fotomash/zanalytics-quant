"""Validate required modules import before starting service."""

import importlib
import sys

from services.common import get_logger

REQUIRED_MODULES = [
    "confluent_kafka",
    "requests",
    "services.vectorization_service.brown_vector_store_integration",
    "services.vectorization_service.pipeline",
]

logger = get_logger(__name__)


def main() -> None:
    missing: list[str] = []
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover - defensive
            missing.append(f"{module}: {exc}")
    if missing:
        for msg in missing:
            logger.error("Failed to import %s", msg)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
